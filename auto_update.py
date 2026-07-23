"""GitHub Releases updater for the portable Windows build."""

from __future__ import annotations

import ctypes
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

from PyQt5 import sip
from PyQt5.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt5.QtWidgets import QApplication, QLabel, QMessageBox, QPushButton, QScrollArea

from actpilot.messagebox import show_message
from version import __version__


GITHUB_REPOSITORY = "temkafox/FTA"
RELEASE_API = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/releases/latest"
ASSET_NAME = "ActPilot-PoE1.exe"

_UPDATE_LABELS = {QMessageBox.Yes: "Установить", QMessageBox.No: "Позже"}


class NoPublishedRelease(RuntimeError):
    pass


_ACTIVE_WORKERS: set = set()


def _launch_worker(worker: "UpdateWorker") -> None:
    # Держит QThread живым независимо от судьбы диалога, из которого он запущен
    _ACTIVE_WORKERS.add(worker)
    worker.finished.connect(lambda: _ACTIVE_WORKERS.discard(worker))
    worker.start()


def _version_tuple(value: str) -> tuple[int, ...]:
    value = value.strip().lower().lstrip("v").split("-", 1)[0]
    try:
        return tuple(int(part) for part in value.split("."))
    except ValueError:
        return (0,)


def get_latest_release() -> dict:
    request = urllib.request.Request(
        RELEASE_API,
        headers={"Accept": "application/vnd.github+json", "User-Agent": f"ActPilot/{__version__}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            release = json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise NoPublishedRelease(
                "В GitHub пока нет опубликованного Release или репозиторий недоступен публично."
            ) from exc
        raise
    asset = next((item for item in release.get("assets", []) if item.get("name") == ASSET_NAME), None)
    if asset is None:
        raise RuntimeError(f"В релизе нет файла {ASSET_NAME}")
    return {
        "version": str(release.get("tag_name", "")).lstrip("v"),
        "url": asset["browser_download_url"],
        "notes": str(release.get("body") or ""),
    }


class UpdateWorker(QThread):
    checked = pyqtSignal(object)
    downloaded = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, download: bool = False, release: dict | None = None, parent=None):
        super().__init__(parent)
        self.download = download
        self.release = release

    def run(self):
        try:
            if not self.download:
                self.checked.emit(get_latest_release())
                return
            if not self.release:
                raise RuntimeError("Не получены данные релиза")
            destination = Path(sys.executable).with_name("ActPilot-PoE1.update.exe")
            destination.unlink(missing_ok=True)
            request = urllib.request.Request(
                self.release["url"], headers={"User-Agent": f"ActPilot/{__version__}"}
            )
            with urllib.request.urlopen(request, timeout=60) as source, destination.open("wb") as target:
                shutil.copyfileobj(source, target)
            if destination.stat().st_size < 1_000_000:
                destination.unlink(missing_ok=True)
                raise RuntimeError("Скачанный файл слишком мал и похож на ошибку сервера")
            self.downloaded.emit(str(destination))
        except Exception as exc:
            self.failed.emit(str(exc))


def add_update_controls(dialog) -> None:
    """Append version/check controls to the existing settings dialog."""
    scrolls = dialog.findChildren(QScrollArea)
    if not scrolls:
        return
    layout = scrolls[0].widget().layout()
    label = QLabel(f"ActPilot  •  версия {__version__}")
    label.setAlignment(Qt.AlignCenter)
    label.setStyleSheet("color:#918b80; margin-top:8px; font-size:12px;")
    button = QPushButton("Проверить обновления")
    button.setObjectName("secondaryButton")
    button.setMinimumHeight(38)
    button.clicked.connect(lambda: _check_from_dialog(dialog, button))
    layout.addWidget(label)
    layout.addWidget(button)


def _cleanup_stale_update_file() -> None:
    stale = Path(sys.executable).with_name("ActPilot-PoE1.update.exe")
    if Path(sys.executable).resolve() == stale.resolve():
        return
    try:
        stale.unlink(missing_ok=True)
    except OSError:
        pass


def schedule_startup_check(window, delay_ms: int = 3000) -> None:
    """Silently check on startup and only interrupt when an update exists."""
    if not getattr(sys, "frozen", False):
        return
    _cleanup_stale_update_file()
    QTimer.singleShot(delay_ms, lambda: _check_on_startup(window))


def _check_on_startup(window) -> None:
    worker = UpdateWorker()

    def checked(release: dict):
        if sip.isdeleted(window):
            return
        if _version_tuple(release["version"]) <= _version_tuple(__version__):
            return
        answer = show_message(
            window,
            QMessageBox.Question,
            "Доступно обновление",
            f"Доступна версия {release['version']} (установлена {__version__}).\n\n"
            "Скачать и установить сейчас?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
            _UPDATE_LABELS,
        )
        if answer == QMessageBox.Yes:
            _download_from_dialog(window, None, release)

    worker.checked.connect(checked)
    # Startup checks are deliberately quiet on 404, offline mode and timeouts.
    _launch_worker(worker)


def _check_from_dialog(dialog, button: QPushButton) -> None:
    if not getattr(sys, "frozen", False):
        show_message(
            dialog,
            QMessageBox.Information,
            "Обновления",
            "Обновление доступно только в собранной EXE-версии.",
        )
        return
    button.setEnabled(False)
    button.setText("Проверяем…")
    worker = UpdateWorker()

    def checked(release: dict):
        if sip.isdeleted(button):
            return
        button.setEnabled(True)
        button.setText("Проверить обновления")
        if _version_tuple(release["version"]) <= _version_tuple(__version__):
            show_message(
                dialog,
                QMessageBox.Information,
                "Обновления",
                f"У вас актуальная версия {__version__}.",
            )
            return
        answer = show_message(
            dialog,
            QMessageBox.Question,
            "Доступно обновление",
            f"Доступна версия {release['version']} (установлена {__version__}).\n\nСкачать и установить?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
            _UPDATE_LABELS,
        )
        if answer == QMessageBox.Yes:
            _download_from_dialog(dialog, button, release)

    worker.checked.connect(checked)
    worker.failed.connect(lambda error: _show_error(dialog, button, error))
    _launch_worker(worker)


def _download_from_dialog(dialog, button: QPushButton | None, release: dict) -> None:
    if button is not None:
        button.setEnabled(False)
        button.setText("Скачиваем обновление…")
    worker = UpdateWorker(download=True, release=release)

    def downloaded(path: str):
        target = str(Path(sys.executable).resolve())
        subprocess.Popen([path, "--apply-update", target, str(os.getpid())], close_fds=True)
        QApplication.quit()

    worker.downloaded.connect(downloaded)
    worker.failed.connect(lambda error: _show_error(dialog, button, error))
    _launch_worker(worker)


def _show_error(dialog, button: QPushButton | None, error: str) -> None:
    if button is not None and not sip.isdeleted(button):
        button.setEnabled(True)
        button.setText("Проверить обновления")
    show_message(
        dialog,
        QMessageBox.Critical,
        "Ошибка обновления",
        f"Не удалось обновить ActPilot:\n{error}",
    )


def apply_pending_update(argv: list[str]) -> bool:
    """Run by the freshly downloaded EXE before importing the main UI."""
    if len(argv) < 4 or argv[1] != "--apply-update":
        return False
    target = Path(argv[2]).resolve()
    try:
        pid = int(argv[3])
    except ValueError:
        return True

    if os.name == "nt":
        synchronize = 0x00100000
        handle = ctypes.windll.kernel32.OpenProcess(synchronize, False, pid)
        if handle:
            ctypes.windll.kernel32.WaitForSingleObject(handle, 30_000)
            ctypes.windll.kernel32.CloseHandle(handle)
    else:
        time.sleep(2)

    source = Path(sys.executable).resolve()
    for _ in range(30):
        try:
            shutil.copy2(source, target)
            subprocess.Popen([str(target)], close_fds=True)
            return True
        except OSError:
            time.sleep(0.5)
    return True
