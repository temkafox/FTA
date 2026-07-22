"""PoE 1 polish: visible build button, Client.txt setting and PoEDB gem details."""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt5.QtCore import QPointF, QSize, Qt
from PyQt5.QtGui import QColor, QFont, QIcon, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import (
    QApplication, QDialog, QFileDialog, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QScrollArea, QWidget,
)

import main as legacy
import release_poe1_v34 as previous
from poe1_gem_widgets_v8 import PoedbGemChains
from poe1_widgets import find_client_log


def build_tree_icon(size=22):
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    gold = QColor("#c9a35a")
    painter.setPen(QPen(gold, 1.5))
    points = [QPointF(size * .50, size * .22), QPointF(size * .25, size * .70), QPointF(size * .75, size * .70)]
    painter.drawLine(points[0], points[1])
    painter.drawLine(points[0], points[2])
    painter.drawLine(points[1], points[2])
    painter.setBrush(QColor("#18150f"))
    for point in points:
        painter.drawEllipse(point, 2.8, 2.8)
    painter.end()
    return QIcon(pixmap)


class Poe1SettingsDialog(legacy.SettingsDialog):
    def __init__(self, settings, parent=None):
        super().__init__(settings, parent)
        screen = QApplication.primaryScreen()
        max_height = int(screen.availableGeometry().height() * .88) if screen else 640
        self.setFixedHeight(min(640, max_height))

        scrolls = self.findChildren(QScrollArea)
        content_layout = scrolls[0].widget().layout()
        label = QLabel("Client.txt (Path of Exile 1)")
        label.setFont(QFont("Segoe UI", 10))
        label.setStyleSheet(f"color:{legacy.Style.TEXT_MUTED};")
        content_layout.addWidget(label)

        row_widget = QWidget()
        row = QHBoxLayout(row_widget)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        self.client_path_input = QLineEdit(settings.get("poe1_client_path", ""))
        self.client_path_input.setPlaceholderText("Автопоиск или путь к Client.txt")
        self.client_path_input.setToolTip(
            "Оставьте пустым для автоматического поиска Client.txt"
        )
        self.client_path_input.setStyleSheet(self.hotkey_input.styleSheet())
        self.client_path_input.setFixedHeight(40)
        row.addWidget(self.client_path_input, 1)
        browse = QPushButton("…")
        browse.setFixedSize(40, 40)
        browse.setCursor(Qt.PointingHandCursor)
        browse.setStyleSheet(f"""
            QPushButton {{background:{legacy.Style.BG_SECONDARY}; color:{legacy.Style.TEXT_PRIMARY};
                border:1px solid {legacy.Style.BORDER}; border-radius:{legacy.Style.RAD_S}px;}}
            QPushButton:hover {{border-color:{legacy.Style.ACCENT}; background:{legacy.Style.HOVER};}}
        """)
        browse.clicked.connect(self._browse_client_log)
        row.addWidget(browse)
        content_layout.addWidget(row_widget)

    def _browse_client_log(self):
        current = self.client_path_input.text().strip()
        start = str(Path(current).parent) if current else ""
        path, _ = QFileDialog.getOpenFileName(
            self, "Выберите Client.txt", start, "Client log (Client.txt);;Text files (*.txt)",
        )
        if path:
            self.client_path_input.setText(path)

    def get_settings(self):
        settings = super().get_settings()
        settings["poe1_client_path"] = self.client_path_input.text().strip()
        return settings


class PolishedBuildDialog(previous.AssetFramedBuildDialog):
    def __init__(self, overlay):
        super().__init__(overlay)
        self.step_context.clear()
        self.step_context.hide()
        self.step_context.setMaximumHeight(0)

        old_gems = self.gem_links
        gem_layout = old_gems.parentWidget().layout()
        index = gem_layout.indexOf(old_gems)
        gem_layout.removeWidget(old_gems)
        old_gems.deleteLater()
        self.gem_links = PoedbGemChains()
        self.gem_links.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.gem_links.body.setStyleSheet("background:rgba(2,4,4,0.38);")
        gem_layout.insertWidget(index, self.gem_links, 1)
        self._configure_client_monitor()
        self.reload()

    def _configure_client_monitor(self):
        self.monitor._timer.stop()
        configured = str(self.overlay.settings.get("poe1_client_path", "")).strip()
        self.monitor.path = Path(configured) if configured else find_client_log()
        self.monitor._position = 0
        self.monitor.start()


class PolishedOverlay(previous.AssetFramedOverlay):
    def _setup_ui(self):
        super()._setup_ui()
        self._style_build_button()

    def _refresh_header(self):
        super()._refresh_header()
        self._style_build_button()

    def _style_build_button(self):
        if not hasattr(self, "build_btn"):
            return
        self.build_btn.setText("")
        self.build_btn.setIcon(build_tree_icon())
        self.build_btn.setIconSize(QSize(22, 22))
        self.build_btn.setStyleSheet("""
            QPushButton { background:transparent; border:0; padding:0; }
            QPushButton:hover { background:rgba(122,83,30,.18); border:0; }
            QPushButton:pressed { background:rgba(172,124,47,.24); }
        """)

    def _settings(self):
        overlay_was_visible = self.isVisible()
        layout_was_visible = bool(
            self._layout_dialog is not None and self._layout_dialog.isVisible()
        )
        build_was_visible = bool(
            self._build_dialog is not None and self._build_dialog.isVisible()
        )
        regex_was_visible = bool(
            getattr(self, "_regex_dialog", None) is not None
            and self._regex_dialog.isVisible()
        )
        if layout_was_visible:
            self._layout_dialog.hide()
        if build_was_visible:
            self._build_dialog.hide()
        if regex_was_visible:
            # hide() эмитит hidden -> _restore_after_regex; без сброса state оверлей всплывёт поверх настроек
            self._regex_restore_state = None
            self._regex_dialog.hide()
        dialog = Poe1SettingsDialog(self.settings, None)
        dialog.move(self.x() + (self.width() - dialog.width()) // 2, self.y() + 40)
        if overlay_was_visible:
            self.hide()
        result = dialog.exec_()
        if overlay_was_visible:
            self.show()
            self.raise_()
        if layout_was_visible and self._layout_dialog is not None:
            self._layout_dialog.show()
            self._layout_dialog.raise_()
        if build_was_visible and self._build_dialog is not None:
            self._build_dialog.show()
            self._build_dialog.raise_()
        if regex_was_visible and self._regex_dialog is not None:
            self._regex_dialog.show()
            self._regex_dialog.raise_()
        if result != QDialog.Accepted:
            return
        old_game = self.game
        self.settings = dialog.get_settings()
        legacy.save_json(legacy.SETTINGS_FILE, self.settings)
        self.hotkey.restart(self.settings["hotkey"])
        self._start_hotkey()
        self._update_opacity()
        self._apply_click_through_mode()
        new_scale = float(self.settings.get("ui_scale", legacy.DEFAULT_SETTINGS["ui_scale"]))
        self._apply_ui_scale(self._ui_scale, new_scale)
        self._ui_scale = new_scale
        new_game = self.settings.get("game", legacy.DEFAULT_SETTINGS["game"])
        if new_game != old_game:
            self._close_layout_dialog()
            self._save_progress()
            self._switch_game(new_game)
        if self._build_dialog is not None:
            self._build_dialog._configure_client_monitor()
        if dialog.should_reset:
            self.content.reset()
            self.timer.reset()
            self._save_progress()

    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = PolishedBuildDialog(self)
            self._build_dialog.finished.connect(
                lambda _: setattr(self, "_build_dialog", None)
            )
        self._build_dialog.reload()
        self._build_dialog.show()
        self._build_dialog.raise_()
        self._build_dialog.activateWindow()


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setApplicationName(legacy.APP_NAME)
    app.setApplicationDisplayName(legacy.APP_NAME + " — PoE 1")
    legacy.ensure_cormorant_loaded()
    app.setFont(QFont("Segoe UI", 10))
    window = PolishedOverlay()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
