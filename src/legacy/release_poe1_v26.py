"""PoE 1 release with restored native coordinates for ascendancy nodes."""

from __future__ import annotations

import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication

import main as legacy
import release_poe1_v25 as previous
from poe1_tree_renderer_v14 import RestoredAscendancyTreeCanvas


class RestoredAscendancyBuildDialog(previous.NativeAscendancyBuildDialog):
    def __init__(self, overlay):
        super().__init__(overlay)
        old_tree = self.tree_canvas
        tree_layout = old_tree.parentWidget().layout()
        tree_index = tree_layout.indexOf(old_tree)
        selected_masteries = dict(old_tree.selected_masteries)
        tree_layout.removeWidget(old_tree)
        old_tree.deleteLater()
        self.tree_canvas = RestoredAscendancyTreeCanvas()
        self.tree_canvas.selected_masteries = selected_masteries
        tree_layout.insertWidget(tree_index, self.tree_canvas, 1)
        try:
            self.ascendancy_button.clicked.disconnect()
        except TypeError:
            pass
        self.ascendancy_button.clicked.connect(self.tree_canvas.fit_ascendancy)
        self._tree_initialized = False
        self._focused_stage_key = None
        self.reload()


class RestoredAscendancyOverlay(previous.NativeAscendancyOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = RestoredAscendancyBuildDialog(self)
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
    app.setApplicationDisplayName(legacy.APP_NAME + " — PoE 1 CLEAN")
    legacy.ensure_cormorant_loaded()
    app.setFont(QFont("Segoe UI", 10))
    window = RestoredAscendancyOverlay()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
