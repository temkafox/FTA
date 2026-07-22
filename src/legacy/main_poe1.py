"""ActPilot PoE 1 launcher with character profiles and PoB leveling view."""

from __future__ import annotations

import html
import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication, QComboBox, QDialog, QFrame, QHBoxLayout, QInputDialog,
    QLabel, QMessageBox, QPushButton, QScrollArea, QTabWidget, QTextEdit,
    QVBoxLayout, QWidget,
)

import main as legacy
from poe1_builds import (
    LEVEL_MAX, LEVEL_MIN, PobImportError, Poe1ProfileStore, clamp_level,
    new_profile, parse_pob, stage_for_level,
)


PROFILE_FILE = legacy.DATA_DIR / "poe1_characters.json"


def button_style(accent=False):
    background = legacy.Style.ACCENT if accent else legacy.Style.BG_SECONDARY
    color = legacy.Style.BG if accent else legacy.Style.TEXT_SECONDARY
    return f"""
        QPushButton {{
            background: {background}; border: 1px solid {legacy.Style.BORDER};
            border-radius: 7px; color: {color}; padding: 7px 12px;
        }}
        QPushButton:hover {{ border-color: {legacy.Style.ACCENT}; color: white; }}
    """


class PobImportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Импорт Path of Building — PoE 1")
        self.resize(620, 430)
        self.setStyleSheet(
            f"QDialog {{ background:{legacy.Style.BG}; color:{legacy.Style.TEXT_PRIMARY}; }}"
        )
        layout = QVBoxLayout(self)
        title = QLabel("Вставьте полный код Export Build из Path of Building")
        title.setFont(QFont("Segoe UI", 13, QFont.DemiBold))
        layout.addWidget(title)
        hint = QLabel(
            "Лучше использовать leveling PoB с деревьями и Skill Sets, "
            "названными Level 12, Level 24 и т. п. Ссылки pobb.in пока не загружаются."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color:{legacy.Style.TEXT_MUTED};")
        layout.addWidget(hint)
        self.editor = QTextEdit()
        self.editor.setPlaceholderText("PoB code или <PathOfBuilding>...</PathOfBuilding>")
        self.editor.setStyleSheet(
            f"background:{legacy.Style.BG_SECONDARY}; color:{legacy.Style.TEXT_PRIMARY}; "
            f"border:1px solid {legacy.Style.BORDER}; padding:8px;"
        )
        layout.addWidget(self.editor, 1)
        row = QHBoxLayout()
        cancel = QPushButton("Отмена")
        cancel.setStyleSheet(button_style())
        cancel.clicked.connect(self.reject)
        accept = QPushButton("Импортировать")
        accept.setStyleSheet(button_style(True))
        accept.clicked.connect(self.accept)
        row.addStretch()
        row.addWidget(cancel)
        row.addWidget(accept)
        layout.addLayout(row)

    def source(self):
        return self.editor.toPlainText().strip()


class Poe1Overlay(legacy.Overlay):
    def __init__(self):
        self.profile_store = Poe1ProfileStore(PROFILE_FILE)
        legacy_progress = legacy.load_json(legacy.get_progress_file(legacy.GAME_POE1), {})
        self.profile_data = self.profile_store.load(legacy_progress)
        self._profile_switching = False
        self._build_dialog = None
        super().__init__()

    def _setup_ui(self):
        super()._setup_ui()
        self.build_btn = legacy.make_icon_button(
            "build", "◆", legacy.Style.BTN_SIZE, self._open_build_progress, self.header
        )
        self.build_btn.setToolTip("Персонаж, камни и дерево PoE 1")
        header_layout = self.header.layout()
        settings_index = header_layout.indexOf(self.settings_btn)
        header_layout.insertWidget(settings_index, self.build_btn, 0, Qt.AlignVCenter)
        self.build_btn.setVisible(self.game == legacy.GAME_POE1)

    def _refresh_header(self):
        super()._refresh_header()
        if hasattr(self, "build_btn"):
            self._refresh_icon_button(self.build_btn, "build", "◆")

    def _switch_game(self, game):
        super()._switch_game(game)
        if hasattr(self, "build_btn"):
            self.build_btn.setVisible(game == legacy.GAME_POE1)
        if game != legacy.GAME_POE1 and self._build_dialog is not None:
            self._build_dialog.close()

    def active_profile(self):
        active_id = self.profile_data.get("active_profile_id")
        for profile in self.profile_data["profiles"]:
            if profile.get("id") == active_id:
                return profile
        profile = self.profile_data["profiles"][0]
        self.profile_data["active_profile_id"] = profile["id"]
        return profile

    def save_profiles(self):
        self.profile_store.save(self.profile_data)

    def create_profile(self, name):
        if self.game == legacy.GAME_POE1:
            self._save_progress()
        profile = new_profile(name)
        self.profile_data["profiles"].append(profile)
        self.profile_data["active_profile_id"] = profile["id"]
        self.save_profiles()
        self._load_profile_campaign()

    def switch_profile(self, profile_id):
        if profile_id == self.profile_data.get("active_profile_id"):
            return
        if self.game == legacy.GAME_POE1:
            self._save_progress()
        self.profile_data["active_profile_id"] = profile_id
        self.save_profiles()
        self._load_profile_campaign()

    def _load_profile_campaign(self):
        self._profile_switching = True
        try:
            self.content.reset()
            self.timer.reset()
            data = self.active_profile().get("campaign", {})
            if "steps" in data:
                self.content.set_state(data["steps"])
            if "timer" in data:
                self.timer.set_state(data["timer"])
            self._update_progress_bar()
        finally:
            self._profile_switching = False

    def _save_progress(self):
        if getattr(self, "_profile_switching", False):
            return
        if getattr(self, "game", None) != legacy.GAME_POE1:
            return super()._save_progress()
        if not hasattr(self, "content"):
            return
        self.active_profile()["campaign"] = {
            "steps": self.content.get_state(),
            "timer": self.timer.get_state(),
        }
        self.save_profiles()

    def _load_progress(self):
        if getattr(self, "game", None) != legacy.GAME_POE1:
            return super()._load_progress()
        self._load_profile_campaign()

    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = BuildProgressDialog(self)
            self._build_dialog.finished.connect(lambda _: setattr(self, "_build_dialog", None))
        self._build_dialog.reload()
        self._build_dialog.show()
        self._build_dialog.raise_()
        self._build_dialog.activateWindow()

    def closeEvent(self, event):
        if self._build_dialog is not None:
            self._build_dialog.close()
        super().closeEvent(event)


from actpilot.build_dialog import BuildProgressDialog


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setApplicationName(legacy.APP_NAME)
    app.setApplicationDisplayName(legacy.APP_NAME + " — PoE 1")
    legacy.ensure_cormorant_loaded()
    app.setFont(QFont("Segoe UI", 10))
    window = Poe1Overlay()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
