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

from PyQt5.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt5.QtWidgets import QApplication, QLabel, QMessageBox, QPushButton, QScrollArea

from version import __version__


GITHUB_REPOSITORY = "temkafox/FTA"
RELEASE_API = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/releases/latest"
ASSET_NAME = "ActPilot-PoE1.exe"

UPDATE_DIALOG_STYLE = """
QMessageBox {
    background-color: #17181d;
}
QMessageBox QLabel {
    color: #f2eee5;
    background-color: transparent;
    font-size: 13px;
}
QMessageBox QLabel#qt_msgbox_label {
    min-width: 310px;
}
QMessageBox QPushButton {
    min-width: 88px;
    min-height: 30px;
    padding: 3px 14px;
    color: #f2eee5;
    background-color: #292b32;
    border: 1px solid #555966;
    border-radius: 6px;
}
QMessageBox QPushButton:hover {
    background-color: #363943;
    border-color: #d0aa61;
}
QMessageBox QPushButton:default {
    color: #17181d;
    background-color: #d0aa61;
    border-color: #e3bf77;
    font-weight: 600;
}
"""


class NoPublishedRelease(RuntimeError):
    pass


def _show_message(
    parent,
    icon: QMessageBox.Icon,
    title: str,
    text: str,
    buttons: QMessageBox.StandardButtons = QMessageBox.Ok,
    default_button: QMessageBox.StandardButton = QMessageBox.NoButton,
) -> int:
    """Show an updater message that remains readable under the app's dark theme."""
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setIcon(icon)
    box.setText(text)
    box.setStandardButtons(buttons)
    if default_button != QMessageBox.NoButton:
        box.setDefaultButton(default_button)
    box.setStyleSheet(UPDATE_DIALOG_STYLE)
    return box.exec_()


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


def schedule_startup_check(window, delay_ms: int = 3000) -> None:
    """Silently check on startup and only interrupt when an update exists."""
    if not getattr(sys, "frozen", False):
        return
    QTimer.singleShot(delay_ms, lambda: _check_on_startup(window))


def _check_on_startup(window) -> None:
    worker = UpdateWorker(parent=window)
    window._startup_update_worker = worker

    def checked(release: dict):
        if _version_tuple(release["version"]) <= _version_tuple(__version__):
            return
        answer = _show_message(
            window,
            QMessageBox.Question,
            "Доступно обновление",
            f"Доступна версия {release['version']} (установлена {__version__}).\n\n"
            "Скачать и установить сейчас?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if answer == QMessageBox.Yes:
            _download_from_dialog(window, None, release)

    worker.checked.connect(checked)
    # Startup checks are deliberately quiet on 404, offline mode and timeouts.
    worker.start()


def _check_from_dialog(dialog, button: QPushButton) -> None:
    if not getattr(sys, "frozen", False):
        _show_message(
            dialog,
            QMessageBox.Information,
            "Обновления",
            "Обновление доступно только в собранной EXE-версии.",
        )
        return
    button.setEnabled(False)
    button.setText("Проверяем…")
    worker = UpdateWorker(parent=dialog)
    dialog._check_update_worker = worker

    def checked(release: dict):
        button.setEnabled(True)
        button.setText("Проверить обновления")
        if _version_tuple(release["version"]) <= _version_tuple(__version__):
            _show_message(
                dialog,
                QMessageBox.Information,
                "Обновления",
                f"У вас актуальная версия {__version__}.",
            )
            return
        answer = _show_message(
            dialog,
            QMessageBox.Question,
            "Доступно обновление",
            f"Доступна версия {release['version']} (установлена {__version__}).\n\nСкачать и установить?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if answer == QMessageBox.Yes:
            _download_from_dialog(dialog, button, release)

    worker.checked.connect(checked)
    worker.failed.connect(lambda error: _show_error(dialog, button, error))
    worker.start()


def _download_from_dialog(dialog, button: QPushButton | None, release: dict) -> None:
    if button is not None:
        button.setEnabled(False)
        button.setText("Скачиваем обновление…")
    worker = UpdateWorker(download=True, release=release, parent=dialog)
    # Keep both thread objects alive: the check thread can still be finishing
    # while the download thread is being started from its result signal.
    dialog._download_update_worker = worker

    def downloaded(path: str):
        target = str(Path(sys.executable).resolve())
        subprocess.Popen([path, "--apply-update", target, str(os.getpid())], close_fds=True)
        QApplication.quit()

    worker.downloaded.connect(downloaded)
    worker.failed.connect(lambda error: _show_error(dialog, button, error))
    worker.start()


def _show_error(dialog, button: QPushButton | None, error: str) -> None:
    if button is not None:
        button.setEnabled(True)
        button.setText("Проверить обновления")
    _show_message(
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
