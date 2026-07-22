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


from actpilot.overlay import Poe1Overlay


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
