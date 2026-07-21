"""PoE 1: separate mastery, fixed Russian header and Q/B gem acquisition."""

from __future__ import annotations

import sys

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication

import main as legacy
import release_poe1_v28 as previous
import release_poe1_v27 as fallback_renderer
from poe1_gem_progression import links_at_level
from poe1_gem_widgets_v7 import AcquisitionGemChains
from poe1_level_plan_v2 import stage_at_level
from poe1_level_plan_v12 import mastery_separated_plan
from poe1_tree_renderer_v18 import SeparateMasteryTreeCanvas
from release_poe1_v8 import TREE_GRAPH


class MasteryAndQuestBuildDialog(previous.StrictNearestBuildDialog):
    def __init__(self, overlay):
        self._v32_ready = False
        super().__init__(overlay)

        old_gems = self.gem_links
        gem_layout = old_gems.parentWidget().layout()
        gem_index = gem_layout.indexOf(old_gems)
        gem_layout.removeWidget(old_gems)
        old_gems.deleteLater()
        self.gem_links = AcquisitionGemChains()
        self.gem_links.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        gem_layout.insertWidget(gem_index, self.gem_links, 1)

        old_tree = self.tree_canvas
        tree_layout = old_tree.parentWidget().layout()
        tree_index = tree_layout.indexOf(old_tree)
        selected_masteries = dict(old_tree.selected_masteries)
        tree_layout.removeWidget(old_tree)
        old_tree.deleteLater()
        self.tree_canvas = SeparateMasteryTreeCanvas()
        self.tree_canvas.selected_masteries = selected_masteries
        tree_layout.insertWidget(tree_index, self.tree_canvas, 1)
        try:
            self.ascendancy_button.clicked.disconnect()
        except TypeError:
            pass
        self.ascendancy_button.clicked.connect(self.tree_canvas.fit_ascendancy)

        self._tree_initialized = False
        self._focused_stage_key = None
        self._apply_overlay_style()
        self._v32_ready = True
        self.reload()

    def _render_gems(self, build, level):
        if not self._v32_ready:
            return super()._render_gems(build, level)
        self.gem_links.set_character_class(build.get("class", "") if build else "")
        if not build:
            self.gem_links.set_links("Импортируйте PoB", [])
            return
        stage = stage_at_level(build.get("gem_sets", []), level)
        if not stage:
            self.gem_links.set_links("Связки не найдены", [])
            return
        self.gem_links.set_links(
            stage.get("title", "Связки"),
            links_at_level(stage.get("links", []), level),
        )
        self.status.setText(
            "Q — награда за квест · B — купить у продавца · наведите на камень для деталей"
        )

    def _render_tree(self, build, level):
        if not self._v32_ready:
            return fallback_renderer.LocalizedOverlayBuildDialog._render_tree(self, build, level)
        if not build:
            self.tree_stage_label.setText("Импортируйте PoB")
            self.tree_canvas.set_quest_progression([], [], [], {}, {})
            self.tree_canvas.set_mastery_progression([])
            self.tree_canvas.set_ascendancy_build(None, level)
            return
        plan = mastery_separated_plan(
            build.get("trees", []), level, TREE_GRAPH,
            self.tree_canvas.positions, self.tree_canvas.nodes,
        )
        target = plan.get("target")
        if not target:
            self.tree_stage_label.setText("Дерево в PoB не найдено")
            self.tree_canvas.set_quest_progression([], [], [], {}, {})
            self.tree_canvas.set_mastery_progression([])
            self.tree_canvas.set_ascendancy_build(build, level)
            return

        is_mastery = lambda node: self.tree_canvas.nodes.get(str(node), {}).get("isMastery")
        completed_mastery = [node for node in plan["completed"] if is_mastery(node)]
        completed_regular = [node for node in plan["completed"] if not is_mastery(node)]
        immediate = plan["upcoming"][:1]
        next_mastery = immediate[0] if immediate and is_mastery(immediate[0]) else None
        immediate_regular = [] if next_mastery is not None else immediate
        visible_plan = completed_regular + immediate_regular

        old_center, old_scale = self.tree_canvas.center, self.tree_canvas.scale
        self.tree_canvas.set_quest_progression(
            visible_plan, completed_regular, immediate_regular,
            plan["node_levels"], {},
        )
        self.tree_canvas.set_masteries(target.get("masteries", ""))
        self.tree_canvas.set_mastery_progression(completed_mastery, next_mastery)
        self.tree_canvas.set_ascendancy_build(build, level)
        self.ascendancy_button.setEnabled(bool(self.tree_canvas.ascendancy.get("nodes")))
        if self._tree_initialized:
            self.tree_canvas.center, self.tree_canvas.scale = old_center, old_scale
            self.tree_canvas.update()
        else:
            self._tree_initialized = True

        first = immediate[0] if immediate else None
        first_key = str(first) if first is not None else ""
        first_name = (
            self.tree_canvas.nodes.get(first_key, {}).get("name", "Passive")
            if first else "этап завершён"
        )
        kind = "следующее мастерство" if next_mastery is not None else "следующая нода"
        self.tree_stage_label.setText(
            f"Уровень персонажа {level} · {kind}: {first_name}"
        )
        focus_key = (level, first_key)
        if focus_key != self._focused_stage_key:
            self._focused_stage_key = focus_key
            if next_mastery is None:
                QTimer.singleShot(0, self._fit_upcoming)


class MasteryAndQuestOverlay(previous.StrictNearestOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = MasteryAndQuestBuildDialog(self)
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
    window = MasteryAndQuestOverlay()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
