"""PoE 1 tree with explicit progression edges and reliable upcoming focus."""

from __future__ import annotations

import sys

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication

import main as legacy
import release_poe1_v35 as previous
from poe1_tree_renderer_v19 import ExplicitProgressionTreeCanvas


class ExplicitRouteBuildDialog(previous.PolishedBuildDialog):
    def __init__(self, overlay):
        self._v36_ready = False
        self._mastery_focus_key = None
        super().__init__(overlay)

        old_tree = self.tree_canvas
        tree_layout = old_tree.parentWidget().layout()
        tree_index = tree_layout.indexOf(old_tree)
        selected_masteries = dict(old_tree.selected_masteries)
        tree_layout.removeWidget(old_tree)
        old_tree.deleteLater()
        self.tree_canvas = ExplicitProgressionTreeCanvas()
        self.tree_canvas.selected_masteries = selected_masteries
        tree_layout.insertWidget(tree_index, self.tree_canvas, 1)
        try:
            self.ascendancy_button.clicked.disconnect()
        except TypeError:
            pass
        self.ascendancy_button.clicked.connect(self.tree_canvas.fit_ascendancy)
        self._tree_initialized = False
        self._focused_stage_key = None
        self._v36_ready = True
        self.reload()

    def _render_tree(self, build, level):
        super()._render_tree(build, level)
        if not self._v36_ready:
            return
        next_mastery = getattr(self.tree_canvas, "next_mastery", None)
        focus_key = (level, next_mastery)
        if next_mastery and focus_key != self._mastery_focus_key:
            self._mastery_focus_key = focus_key
            QTimer.singleShot(0, self.tree_canvas.fit_upcoming)


class ExplicitRouteOverlay(previous.PolishedOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = ExplicitRouteBuildDialog(self)
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
    window = ExplicitRouteOverlay()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
