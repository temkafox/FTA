"""Corrected PoE 1 UI with respec-aware per-level tree updates."""

from __future__ import annotations

import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication

import main as legacy
import main_poe1_target_v3 as v3
from poe1_progression_final import nodes_at_level
from poe1_stage_logic import previous_stage
from poe1_target_widgets import leveling_stage


class FinalBuildDialog(v3.CorrectedBuildDialog):
    def _render_tree(self, build, level):
        if not self._target_ready:
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
        visible_nodes, newly_added = nodes_at_level(
            stage, previous_nodes, level, v3.per_level.TREE_GRAPH
        )
        new_set = set(newly_added)
        before_current_level = [node for node in visible_nodes if str(node) not in new_set]
        old_center, old_scale = self.tree_canvas.center, self.tree_canvas.scale
        self.tree_canvas.set_stage(visible_nodes, before_current_level)
        if self._tree_initialized:
            self.tree_canvas.center, self.tree_canvas.scale = old_center, old_scale
            self.tree_canvas.update()
        else:
            self.tree_canvas.fit_all()
            self._tree_initialized = True
        target_count = sum(
            str(node) in self.tree_canvas.positions for node in stage.get("nodes", [])
        )
        self.tree_stage_label.setText(
            f"Уровень {level} · {stage.get('title', 'Дерево')} · "
            f"{len(self.tree_canvas.selected)}/{target_count} пассивов · "
            f"+{len(self.tree_canvas.added)} сейчас"
        )


class FinalOverlay(v3.CorrectedOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = FinalBuildDialog(self)
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
    window = FinalOverlay()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
