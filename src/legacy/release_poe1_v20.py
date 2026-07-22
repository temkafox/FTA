"""Current PoE 1 release with clean tree and real gem artwork."""

from __future__ import annotations

import sys

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication, QLabel

import main as legacy
import release_poe1_v19 as previous
from poe1_gem_progression import links_at_level
from poe1_gem_widgets_v3 import ArtworkGemChains
from poe1_level_plan_v2 import stage_at_level
from poe1_level_plan_v9 import corrected_semantic_plan
from poe1_tree_fast import ConstructionTreePlaceholder as CleanPassiveTreeCanvas
from release_poe1_v8 import TREE_GRAPH


class CleanArtworkBuildDialog(previous.CorrectedSemanticBuildDialog):
    def __init__(self, overlay):
        self._v20_ready = False
        super().__init__(overlay)

        old_gems = self.gem_links
        gem_layout = old_gems.parentWidget().layout()
        gem_index = gem_layout.indexOf(old_gems)
        gem_layout.removeWidget(old_gems)
        old_gems.deleteLater()
        self.gem_links = ArtworkGemChains()
        self.gem_links.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        gem_layout.insertWidget(gem_index, self.gem_links, 1)

        old_tree = self.tree_canvas
        tree_layout = old_tree.parentWidget().layout()
        tree_index = tree_layout.indexOf(old_tree)
        selected_masteries = dict(old_tree.selected_masteries)
        tree_layout.removeWidget(old_tree)
        old_tree.deleteLater()
        self.tree_canvas = CleanPassiveTreeCanvas()
        self.tree_canvas.selected_masteries = selected_masteries
        tree_layout.insertWidget(tree_index, self.tree_canvas, 1)

        for label in self.tree_canvas.parentWidget().findChildren(QLabel):
            if label is not self.tree_stage_label and ("Зелён" in label.text() or "золот" in label.text()):
                label.setText(
                    "Зелёное — уже взято · золотое — будущий маршрут · "
                    "светлая рамка — следующая нода"
                )
        self._tree_initialized = False
        self._focused_stage_key = None
        self._v20_ready = True
        self.reload()

    def _render_gems(self, build, level):
        if not self._v20_ready:
            return super()._render_gems(build, level)
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
        self.status.setText("Показаны доступные на текущем этапе связки камней")

    def _render_tree(self, build, level):
        if not self._v20_ready:
            return super()._render_tree(build, level)
        if not build:
            self.tree_stage_label.setText("Импортируйте PoB")
            self.tree_canvas.set_quest_progression([], [], [], {}, {})
            return
        plan = corrected_semantic_plan(
            build.get("trees", []), level, TREE_GRAPH,
            self.tree_canvas.positions, self.tree_canvas.nodes,
        )
        target = plan.get("target")
        if not target:
            self.tree_stage_label.setText("Дерево в PoB не найдено")
            self.tree_canvas.set_quest_progression([], [], [], {}, {})
            return
        old_center, old_scale = self.tree_canvas.center, self.tree_canvas.scale
        self.tree_canvas.set_quest_progression(
            plan["planned"], plan["completed"], plan["upcoming"],
            plan["node_levels"], {},
        )
        self.tree_canvas.set_masteries(target.get("masteries", ""))
        if self._tree_initialized:
            self.tree_canvas.center, self.tree_canvas.scale = old_center, old_scale
            self.tree_canvas.update()
        else:
            self._tree_initialized = True
        first = plan["upcoming"][0] if plan["upcoming"] else None
        first_key = str(first) if first is not None else ""
        first_name = self.tree_canvas.nodes.get(first_key, {}).get("name", "Пассив") if first else "этап завершён"
        self.tree_stage_label.setText(
            f"Уровень персонажа {level} · следующая нода: {first_name}"
        )
        focus_key = (level, first_key)
        if focus_key != self._focused_stage_key:
            self._focused_stage_key = focus_key
            QTimer.singleShot(0, self._fit_upcoming)


class CleanArtworkOverlay(previous.CorrectedSemanticOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = CleanArtworkBuildDialog(self)
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
    window = CleanArtworkOverlay()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
