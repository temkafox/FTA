"""PoE 1 release with node acquisition levels and visibly updating gems."""

from __future__ import annotations

import sys

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication

import main as legacy
import release_poe1_v10 as previous
from poe1_gem_progression import links_at_level
from poe1_gem_widgets_v2 import LevelGemChains
from poe1_level_plan_v2 import stage_at_level
from poe1_level_plan_v3 import passive_plan_by_level
from poe1_tree_renderer_v8 import LevelMappedTreeCanvas
from release_poe1_v8 import TREE_GRAPH


class LevelMappedBuildDialog(previous.ScaledGemBuildDialog):
    def __init__(self, overlay):
        self._v11_ready = False
        super().__init__(overlay)

        old_gems = self.gem_links
        gem_layout = old_gems.parentWidget().layout()
        gem_index = gem_layout.indexOf(old_gems)
        gem_layout.removeWidget(old_gems)
        old_gems.deleteLater()
        self.gem_links = LevelGemChains()
        self.gem_links.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        gem_layout.insertWidget(gem_index, self.gem_links, 1)

        old_tree = self.tree_canvas
        tree_layout = old_tree.parentWidget().layout()
        tree_index = tree_layout.indexOf(old_tree)
        selected_masteries = dict(old_tree.selected_masteries)
        tree_layout.removeWidget(old_tree)
        old_tree.deleteLater()
        self.tree_canvas = LevelMappedTreeCanvas()
        self.tree_canvas.selected_masteries = selected_masteries
        tree_layout.insertWidget(tree_index, self.tree_canvas, 1)

        self._tree_initialized = False
        self._focused_stage_key = None
        self._v11_ready = True
        self.reload()

    def _render_gems(self, build, level):
        if not self._v11_ready:
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
        links = links_at_level(stage.get("links", []), level)
        self.gem_links.set_links(f"{title} · уровень {level}", links)
        self.status.setText(
            f"Уровень персонажа {level} · показаны доступные камни и их текущие уровни"
        )

    def _render_tree(self, build, level):
        if not self._v11_ready:
            return super()._render_tree(build, level)
        if not build:
            self.tree_stage_label.setText("Импортируйте PoB")
            self.tree_canvas.set_level_progression([], [], [], {})
            return
        plan = passive_plan_by_level(build.get("trees", []), level, TREE_GRAPH)
        target = plan.get("target")
        if not target:
            self.tree_stage_label.setText("Дерево в PoB не найдено")
            self.tree_canvas.set_level_progression([], [], [], {})
            return

        old_center, old_scale = self.tree_canvas.center, self.tree_canvas.scale
        self.tree_canvas.set_level_progression(
            plan["planned"], plan["completed"], plan["upcoming"], plan["node_levels"]
        )
        self.tree_canvas.set_masteries(target.get("masteries", ""))
        if self._tree_initialized:
            self.tree_canvas.center, self.tree_canvas.scale = old_center, old_scale
            self.tree_canvas.update()
        else:
            self._tree_initialized = True

        first = plan["upcoming"][0] if plan["upcoming"] else None
        first_name = self.tree_canvas.nodes.get(str(first), {}).get("name", "Пассив") if first else "—"
        first_level = plan["node_levels"].get(str(first), "—") if first else "—"
        self.tree_stage_label.setText(
            f"Уровень {level} · зелёное взято {len(self.tree_canvas.completed_nodes)} · "
            f"золотое впереди {len(self.tree_canvas.route_nodes)} · "
            f"следующий: ур. {first_level}, {first_name}"
        )
        focus_key = (level, str(first), first_level)
        if focus_key != self._focused_stage_key:
            self._focused_stage_key = focus_key
            QTimer.singleShot(0, self._fit_upcoming)


class LevelMappedOverlay(previous.ScaledGemOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = LevelMappedBuildDialog(self)
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
    window = LevelMappedOverlay()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
