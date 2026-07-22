"""PoE 1 release with ascendancy integrated into the main tree and copyable gems."""

from __future__ import annotations

import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication

import main as legacy
import release_poe1_v23 as previous
from poe1_gem_widgets_v5 import CopyableGemChains


class IntegratedTreeBuildDialog(previous.ConnectedAscendancyBuildDialog):
    def __init__(self, overlay):
        self._integrated_ready = False
        super().__init__(overlay)

        # The ascendancy now lives inside the main tree canvas.
        if self.left_tabs.count() > 1:
            hidden_ascendancy = self.left_tabs.widget(1)
            self.left_tabs.removeTab(1)
            hidden_ascendancy.hide()
        self.left_tabs.tabBar().hide()

        old_gems = self.gem_links
        gem_layout = old_gems.parentWidget().layout()
        gem_index = gem_layout.indexOf(old_gems)
        gem_layout.removeWidget(old_gems)
        old_gems.deleteLater()
        self.gem_links = CopyableGemChains()
        self.gem_links.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        gem_layout.insertWidget(gem_index, self.gem_links, 1)

        old_tree = self.tree_canvas
        tree_layout = old_tree.parentWidget().layout()
        tree_index = tree_layout.indexOf(old_tree)
        selected_masteries = dict(old_tree.selected_masteries)
        tree_layout.removeWidget(old_tree)
        old_tree.deleteLater()
        self.tree_canvas = IntegratedAscendancyTreeCanvas()
        self.tree_canvas.selected_masteries = selected_masteries
        tree_layout.insertWidget(tree_index, self.tree_canvas, 1)

        self._tree_initialized = False
        self._focused_stage_key = None
        self._integrated_ready = True
        self.reload()

    def _render_tree(self, build, level):
        super()._render_tree(build, level)
        if self._integrated_ready:
            self.tree_canvas.set_ascendancy_build(build, level)


class IntegratedTreeOverlay(previous.ConnectedAscendancyOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = IntegratedTreeBuildDialog(self)
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
    window = IntegratedTreeOverlay()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
