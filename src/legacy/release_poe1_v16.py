"""Current PoE 1 release: level points plus quest books, no bandits."""

from __future__ import annotations

import sys

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication, QLabel

import main as legacy
import release_poe1_v15 as previous
from poe1_level_plan_v6 import book_only_passive_plan
from release_poe1_v8 import TREE_GRAPH


class BookOnlyBuildDialog(previous.QuestAwareBuildDialog):
    def __init__(self, overlay):
        self._v16_ready = False
        super().__init__(overlay)
        for label in self.tree_canvas.parentWidget().findChildren(QLabel):
            if label is not self.tree_stage_label and ("Зелён" in label.text() or "золот" in label.text()):
                label.setText(
                    "Зелёное — взято · золотое — впереди · "
                    "12 — очко уровня · 12К — книга за квест"
                )
        self._tree_initialized = False
        self._focused_stage_key = None
        self._v16_ready = True
        self.reload()

    def _render_tree(self, build, level):
        if not self._v16_ready:
            return super()._render_tree(build, level)
        if not build:
            self.tree_stage_label.setText("Импортируйте PoB")
            self.tree_canvas.set_quest_progression([], [], [], {}, {})
            return
        plan = book_only_passive_plan(build.get("trees", []), level, TREE_GRAPH)
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
            f"Уровень {level} · взято {len(self.tree_canvas.completed_nodes)} · "
            f"следующий {marker}: {first_name} ({source}) · учитываются только книги"
        )
        focus_key = (level, first_key, marker)
        if focus_key != self._focused_stage_key:
            self._focused_stage_key = focus_key
            QTimer.singleShot(0, self._fit_upcoming)


class BookOnlyOverlay(previous.QuestAwareOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = BookOnlyBuildDialog(self)
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
    app.setApplicationDisplayName(legacy.APP_NAME + " — PoE 1 BOOKS")
    legacy.ensure_cormorant_loaded()
    app.setFont(QFont("Segoe UI", 10))
    window = BookOnlyOverlay()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
