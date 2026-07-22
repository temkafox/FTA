"""PoE 1: zoom-safe tree plus simplified level-centric gem editor."""

from __future__ import annotations

import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication

import main as legacy
import release_poe1_v40 as previous
from poe1_manual_editor_v11 import ManualBuildEditor
from actpilot.tree import CachedZoomSafeTreeCanvas as ZoomSafeTreeCanvas


class ClearGemEditorBuildDialog(previous.StableEditorBuildDialog):
    def __init__(self, overlay):
        super().__init__(overlay)
        old_tree = self.tree_canvas
        layout = old_tree.parentWidget().layout()
        index = layout.indexOf(old_tree)
        selected_masteries = dict(old_tree.selected_masteries)
        layout.removeWidget(old_tree)
        old_tree.deleteLater()
        self.tree_canvas = ZoomSafeTreeCanvas()
        self.tree_canvas.selected_masteries = selected_masteries
        layout.insertWidget(index, self.tree_canvas, 1)
        try:
            self.ascendancy_button.clicked.disconnect()
        except TypeError:
            pass
        self.ascendancy_button.clicked.connect(self.tree_canvas.fit_ascendancy)
        self._tree_initialized = False
        self._focused_stage_key = None
        self._mastery_focus_key = None
        self._manual_focus_key = None
        self.reload()

    def _open_manual_editor(self):
        editor = ManualBuildEditor(self.overlay, self)
        if editor.exec_():
            self._tree_initialized = False
            self._focused_stage_key = None
            self._mastery_focus_key = None
            self._manual_focus_key = None
            self.reload()


class ClearGemEditorOverlay(previous.StableEditorOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = ClearGemEditorBuildDialog(self)
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
    window = ClearGemEditorOverlay()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
