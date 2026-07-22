"""Current PoE 1 release with approximate quest passive rewards."""

from __future__ import annotations

import sys

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication, QLabel

import main as legacy
import release_poe1_v14 as previous
from poe1_level_plan_v5 import pob_kills_all_bandits, quest_aware_passive_plan
from poe1_tree_fast import ConstructionTreePlaceholder as QuestAwareTreeCanvas
from release_poe1_v8 import TREE_GRAPH


class QuestAwareBuildDialog(previous.StrictProgressionBuildDialog):
    def __init__(self, overlay):
        self._v15_ready = False
        super().__init__(overlay)
        old_tree = self.tree_canvas
        layout = old_tree.parentWidget().layout()
        index = layout.indexOf(old_tree)
        selected_masteries = dict(old_tree.selected_masteries)
        layout.removeWidget(old_tree)
        old_tree.deleteLater()
        self.tree_canvas = QuestAwareTreeCanvas()
        self.tree_canvas.selected_masteries = selected_masteries
        layout.insertWidget(index, self.tree_canvas, 1)
        for label in self.tree_canvas.parentWidget().findChildren(QLabel):
            if label is not self.tree_stage_label and ("Зелён" in label.text() or "золот" in label.text()):
                label.setText(
                    "Зелёное — взято · золотое — впереди · 12 — очко уровня · "
                    "12К — квестовая книга · 20Б — награда Эрамира"
                )
        self._tree_initialized = False
        self._focused_stage_key = None
        self._v15_ready = True
        self.reload()

    def _render_tree(self, build, level):
        if not self._v15_ready:
            return super()._render_tree(build, level)
        if not build:
            self.tree_stage_label.setText("Импортируйте PoB")
            self.tree_canvas.set_quest_progression([], [], [], {}, {})
            return
        kill_all = pob_kills_all_bandits(build)
        plan = quest_aware_passive_plan(
            build.get("trees", []), level, TREE_GRAPH, kill_all
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
        bandit_text = "Эрамир +1" if kill_all else "помощь бандиту, без очка"
        self.tree_stage_label.setText(
            f"Уровень {level} · взято {len(self.tree_canvas.completed_nodes)} · "
            f"следующий {marker}: {first_name} ({source}) · {bandit_text}"
        )
        focus_key = (level, first_key, marker)
        if focus_key != self._focused_stage_key:
            self._focused_stage_key = focus_key
            QTimer.singleShot(0, self._fit_upcoming)


class QuestAwareOverlay(previous.StrictProgressionOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = QuestAwareBuildDialog(self)
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
    app.setApplicationDisplayName(legacy.APP_NAME + " — PoE 1 QUEST POINTS")
    legacy.ensure_cormorant_loaded()
    app.setFont(QFont("Segoe UI", 10))
    window = QuestAwareOverlay()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
