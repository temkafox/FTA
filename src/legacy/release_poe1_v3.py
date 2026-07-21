"""Current release: full PoB stages, complete edges, clean node renderer."""

from __future__ import annotations

import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication

import main as legacy
import release_poe1_v2 as previous
from poe1_stage_logic import previous_stage
from poe1_target_widgets import leveling_stage
from poe1_tree_renderer_v3 import ConnectedPassiveTreeCanvas


class FullStageBuildDialog(previous.CleanBuildDialog):
    def __init__(self, overlay):
        self._v3_ready = False
        super().__init__(overlay)
        old_canvas = self.tree_canvas
        layout = old_canvas.parentWidget().layout()
        index = layout.indexOf(old_canvas)
        layout.removeWidget(old_canvas)
        old_canvas.deleteLater()
        self.tree_canvas = ConnectedPassiveTreeCanvas()
        layout.insertWidget(index, self.tree_canvas, 1)
        self._tree_initialized = False
        self._v3_ready = True
        self.reload()

    def _render_tree(self, build, level):
        if not self._v3_ready:
            return super()._render_tree(build, level)
        if not build:
            self.tree_stage_label.setText("Импортируйте PoB")
            self.tree_canvas.set_stage([])
            return
        trees = build.get("trees", [])
        stage = leveling_stage(trees, level)
        if not stage:
            self.tree_stage_label.setText("Дерево в PoB не найдено")
            self.tree_canvas.set_stage([])
            return
        previous = previous_stage(trees, stage)
        previous_nodes = previous.get("nodes", []) if previous else []
        old_center, old_scale = self.tree_canvas.center, self.tree_canvas.scale
        self.tree_canvas.set_stage(stage.get("nodes", []), previous_nodes)
        if self._tree_initialized:
            self.tree_canvas.center, self.tree_canvas.scale = old_center, old_scale
            self.tree_canvas.update()
        else:
            self.tree_canvas.fit_all()
            self._tree_initialized = True
        current_count = len(self.tree_canvas.selected)
        added_count = len(self.tree_canvas.added)
        self.tree_stage_label.setText(
            f"Уровень {level} · {stage.get('title', 'Дерево')} · "
            f"{current_count}/{current_count} пассивов · +{added_count} с прошлого этапа"
        )


class FullStageOverlay(previous.CleanOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = FullStageBuildDialog(self)
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
    window = FullStageOverlay()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
