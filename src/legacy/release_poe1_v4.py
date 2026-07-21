"""Current release with opaque tooltips and exact PoB mastery selection."""

from __future__ import annotations

import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication

import main as legacy
import release_poe1_v3 as previous
from poe1_target_widgets import leveling_stage
from poe1_tree_renderer_v4 import MasteryAwareTreeCanvas


class MasteryBuildDialog(previous.FullStageBuildDialog):
    def __init__(self, overlay):
        self._v4_ready = False
        super().__init__(overlay)
        old_canvas = self.tree_canvas
        layout = old_canvas.parentWidget().layout()
        index = layout.indexOf(old_canvas)
        layout.removeWidget(old_canvas)
        old_canvas.deleteLater()
        self.tree_canvas = MasteryAwareTreeCanvas()
        layout.insertWidget(index, self.tree_canvas, 1)
        self._tree_initialized = False
        self._v4_ready = True
        self.reload()

    def _render_tree(self, build, level):
        if not self._v4_ready:
            return super()._render_tree(build, level)
        super()._render_tree(build, level)
        if build:
            stage = leveling_stage(build.get("trees", []), level)
            self.tree_canvas.set_masteries(stage.get("masteries", "") if stage else "")


class MasteryOverlay(previous.FullStageOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = MasteryBuildDialog(self)
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
    window = MasteryOverlay()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
