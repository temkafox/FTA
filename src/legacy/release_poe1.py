"""Current release entry for the PoE 1 ActPilot prototype."""

from __future__ import annotations

import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication

import main as legacy
import main_poe1_corrected as corrected
from poe1_mastery_tree import CompleteTooltipTreeCanvas


class ReleaseBuildDialog(corrected.FinalBuildDialog):
    def __init__(self, overlay):
        super().__init__(overlay)
        old_canvas = self.tree_canvas
        layout = old_canvas.parentWidget().layout()
        index = layout.indexOf(old_canvas)
        layout.removeWidget(old_canvas)
        old_canvas.deleteLater()
        self.tree_canvas = CompleteTooltipTreeCanvas()
        layout.insertWidget(index, self.tree_canvas, 1)
        self._tree_initialized = False
        self.reload()


class ReleaseOverlay(corrected.FinalOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = ReleaseBuildDialog(self)
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
    window = ReleaseOverlay()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
