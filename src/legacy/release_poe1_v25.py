"""PoE 1 release with ascendancy highlighted in its native tree location."""

from __future__ import annotations

import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication, QPushButton

import main as legacy
import main_poe1 as base
import release_poe1_v24 as previous
from poe1_tree_fast import ConstructionTreePlaceholder as NativeAscendancyTreeCanvas


class NativeAscendancyBuildDialog(previous.IntegratedTreeBuildDialog):
    def __init__(self, overlay):
        self._native_asc_ready = False
        super().__init__(overlay)

        old_tree = self.tree_canvas
        tree_page = old_tree.parentWidget()
        tree_layout = tree_page.layout()
        tree_index = tree_layout.indexOf(old_tree)
        selected_masteries = dict(old_tree.selected_masteries)
        tree_layout.removeWidget(old_tree)
        old_tree.deleteLater()
        self.tree_canvas = NativeAscendancyTreeCanvas()
        self.tree_canvas.selected_masteries = selected_masteries
        tree_layout.insertWidget(tree_index, self.tree_canvas, 1)

        header_layout = tree_layout.itemAt(0).layout()
        self.ascendancy_button = QPushButton("К ассенданси")
        self.ascendancy_button.setStyleSheet(base.button_style())
        self.ascendancy_button.clicked.connect(self.tree_canvas.fit_ascendancy)
        header_layout.insertWidget(1, self.ascendancy_button)

        self._tree_initialized = False
        self._focused_stage_key = None
        self._native_asc_ready = True
        self.reload()

    def _render_tree(self, build, level):
        super()._render_tree(build, level)
        if self._native_asc_ready:
            self.tree_canvas.set_ascendancy_build(build, level)
            self.ascendancy_button.setEnabled(bool(self.tree_canvas.ascendancy.get("nodes")))


class NativeAscendancyOverlay(previous.IntegratedTreeOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = NativeAscendancyBuildDialog(self)
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
    window = NativeAscendancyOverlay()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
