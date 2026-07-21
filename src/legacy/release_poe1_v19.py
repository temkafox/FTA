"""Current PoE 1 release with corrected key-node branch ordering."""

from __future__ import annotations

import sys

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication

import main as legacy
import release_poe1_v18 as previous
from poe1_level_plan_v9 import corrected_semantic_plan
from release_poe1_v8 import TREE_GRAPH


class CorrectedSemanticBuildDialog(previous.SemanticPassiveBuildDialog):
    def __init__(self, overlay):
        self._v19_ready = False
        super().__init__(overlay)
        self._tree_initialized = False
        self._focused_stage_key = None
        self._v19_ready = True
        self.reload()

    def _render_tree(self, build, level):
        if not self._v19_ready:
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
            plan["node_levels"], plan["node_markers"],
        )
        self.tree_canvas.set_masteries(target.get("masteries", ""))
        if self._tree_initialized:
            self.tree_canvas.center, self.tree_canvas.scale = old_center, old_scale
            self.tree_canvas.update()
        else:
            self._tree_initialized = True
        first = plan["upcoming"][0] if plan["upcoming"] else None
        first_key = str(first) if first is not None else ""
        first_name = self.tree_canvas.nodes.get(first_key, {}).get("name", "Пассив") if first else "—"
        marker = plan["node_markers"].get(first_key, "—")
        source = plan["node_sources"].get(first_key, "этап завершён")
        self.tree_stage_label.setText(
            f"Уровень {level} · следующий {marker}: {first_name} ({source}) · "
            "кейстоуны берутся при открытии ветки"
        )
        focus_key = (level, first_key, marker)
        if focus_key != self._focused_stage_key:
            self._focused_stage_key = focus_key
            QTimer.singleShot(0, self._fit_upcoming)


class CorrectedSemanticOverlay(previous.SemanticPassiveOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = CorrectedSemanticBuildDialog(self)
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
    app.setApplicationDisplayName(legacy.APP_NAME + " — PoE 1 CURRENT")
    legacy.ensure_cormorant_loaded()
    app.setFont(QFont("Segoe UI", 10))
    window = CorrectedSemanticOverlay()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
