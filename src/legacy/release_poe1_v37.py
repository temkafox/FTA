"""PoE 1 build window with the integrated manual passive and gem editor."""

from __future__ import annotations

import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication, QPushButton

import main as legacy
import release_poe1_v36 as previous
from poe1_manual_editor_v2 import ManualBuildEditor


def _layout_with_widget(layout, target):
    for index in range(layout.count()):
        item = layout.itemAt(index)
        if item.widget() is target:
            return layout
        child = item.layout()
        if child is not None:
            found = _layout_with_widget(child, target)
            if found is not None:
                return found
    return None


class EditableBuildDialog(previous.ExplicitRouteBuildDialog):
    def __init__(self, overlay):
        super().__init__(overlay)
        self.editor_button = QPushButton("Редактор")
        self.editor_button.setCursor(Qt.PointingHandCursor)
        self.editor_button.setToolTip("Вручную выбрать пассивы и этапы связок камней")
        self.editor_button.clicked.connect(self._open_manual_editor)
        self.editor_button.setStyleSheet("""
            QPushButton {background:rgba(91,64,24,.24); color:#d8bd7a;
                border:1px solid rgba(190,145,69,.56); border-radius:5px; padding:5px 11px;}
            QPushButton:hover {background:rgba(122,83,30,.32); color:#f0dfb9; border-color:#d1a85d;}
        """)
        row = _layout_with_widget(self.layout(), self.profile_combo)
        if row is not None:
            row.addWidget(self.editor_button)

    def _open_manual_editor(self):
        editor = ManualBuildEditor(self.overlay, self)
        if editor.exec_():
            self._tree_initialized = False
            self._focused_stage_key = None
            self._mastery_focus_key = None
            self.reload()


class EditableBuildOverlay(previous.ExplicitRouteOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = EditableBuildDialog(self)
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
    window = EditableBuildOverlay()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
