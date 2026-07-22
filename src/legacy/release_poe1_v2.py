"""Current PoE 1 release with clean tree rendering and custom tooltips."""

from __future__ import annotations

import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication

import main as legacy
import release_poe1 as previous
from poe1_tree_fast import ConstructionTreePlaceholder as CleanPassiveTreeCanvas


class CleanBuildDialog(previous.ReleaseBuildDialog):
    def __init__(self, overlay):
        super().__init__(overlay)
        old_canvas = self.tree_canvas
        layout = old_canvas.parentWidget().layout()
        index = layout.indexOf(old_canvas)
        layout.removeWidget(old_canvas)
        old_canvas.deleteLater()
        self.tree_canvas = CleanPassiveTreeCanvas()
        layout.insertWidget(index, self.tree_canvas, 1)
        self._tree_initialized = False
        self.reload()


class CleanOverlay(previous.ReleaseOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = CleanBuildDialog(self)
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
    window = CleanOverlay()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
