"""PoE 1 release with real per-level passive progression and fixed gem ranges."""

from __future__ import annotations

import sys

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication

import main as legacy
import release_poe1_v7 as previous
from actpilot.data_cache import tree_graph
from poe1_level_plan import passive_plan, stage_at_level
from poe1_target_widgets import ROOT
from poe1_tree_fast import ConstructionTreePlaceholder as ProgressionTreeCanvas


TREE_GRAPH = tree_graph(ROOT / "skilltree.json")


class ProgressionBuildDialog(previous.CombinedBuildDialog):
    def __init__(self, overlay):
        self._v8_ready = False
        super().__init__(overlay)
        old_canvas = self.tree_canvas
        layout = old_canvas.parentWidget().layout()
        index = layout.indexOf(old_canvas)
        selected_masteries = dict(old_canvas.selected_masteries)
        layout.removeWidget(old_canvas)
        old_canvas.deleteLater()
        self.tree_canvas = ProgressionTreeCanvas()
        self.tree_canvas.selected_masteries = selected_masteries
        layout.insertWidget(index, self.tree_canvas, 1)
        self._focused_stage_key = None
        self._tree_initialized = False
        self._v8_ready = True
        self.reload()

    def _render_gems(self, build, level):
        if not self._v8_ready:
            return super()._render_gems(build, level)
        if not build:
            self.gem_links.set_links("Импортируйте PoB", [])
            return
        stages = build.get("gem_sets", [])
        stage = stage_at_level(stages, level)
        if not stage:
            self.gem_links.set_links("Связки не найдены", [])
            return
        title = stage.get("title", "Связки")
        self.gem_links.set_links(title, stage.get("links", []))
        future_levels = sorted({
            int(item.get("level", 1)) for item in stages
            if int(item.get("level", 1)) > level
        })
        next_text = f" · следующая смена на {future_levels[0]}" if future_levels else ""
        self.status.setText(
            f"Уровень персонажа {level} · набор камней «{title}»{next_text}"
        )

    def _render_tree(self, build, level):
        if not self._v8_ready:
            return super()._render_tree(build, level)
        if not build:
            self.tree_stage_label.setText("Импортируйте PoB")
            self.tree_canvas.set_progression([], [], [])
            self._focused_stage_key = None
            return

        plan = passive_plan(build.get("trees", []), level, TREE_GRAPH)
        target = plan.get("target")
        if not target:
            self.tree_stage_label.setText("Дерево в PoB не найдено")
            self.tree_canvas.set_progression([], [], [])
            self._focused_stage_key = None
            return

        old_center, old_scale = self.tree_canvas.center, self.tree_canvas.scale
        self.tree_canvas.set_progression(
            plan["planned"], plan["completed"], plan["upcoming"]
        )
        self.tree_canvas.set_masteries(target.get("masteries", ""))
        if self._tree_initialized:
            self.tree_canvas.center, self.tree_canvas.scale = old_center, old_scale
            self.tree_canvas.update()
        else:
            self._tree_initialized = True

        upcoming_names = [
            self.tree_canvas.nodes.get(str(node), {}).get("name", "Пассив")
            for node in plan["upcoming"][:3]
        ]
        next_text = " → ".join(upcoming_names) or "этап завершён"
        self.tree_stage_label.setText(
            f"Уровень {level} · цель: {target.get('title', 'Дерево')} · "
            f"взято {len(self.tree_canvas.completed_nodes)}/{len(self.tree_canvas.selected)} · "
            f"дальше: {next_text}"
        )

        stage_key = (
            level,
            target.get("title", ""),
            tuple(plan["upcoming"][:5]),
        )
        if stage_key != self._focused_stage_key:
            self._focused_stage_key = stage_key
            QTimer.singleShot(0, self._fit_upcoming)


class ProgressionOverlay(previous.CombinedOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = ProgressionBuildDialog(self)
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
    window = ProgressionOverlay()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
