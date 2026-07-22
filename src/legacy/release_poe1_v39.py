"""Manual editor release with exact saved passive/mastery ordering."""

from __future__ import annotations

import sys

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication

import main as legacy
import release_poe1_v32 as standard_renderer
import release_poe1_v38 as previous
from actpilot.build_model import manual_passive_plan


class ExactManualBuildDialog(previous.EditableBuildDialog):
    def __init__(self, overlay):
        self._manual_plan_ready = False
        super().__init__(overlay)
        self._manual_plan_ready = True
        self._manual_focus_key = None
        self._tree_initialized = False
        self.reload()

    def _render_tree(self, build, level):
        if not self._manual_plan_ready or not build or build.get("format") != "actpilot-manual-v1":
            return super()._render_tree(build, level)

        plan = manual_passive_plan(build, level)
        target = plan["target"]
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
            plan["node_levels"], plan["node_markers"],
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
        first_name = self.tree_canvas.nodes.get(str(first), {}).get("name", "этап завершён") if first else "этап завершён"
        used = len(plan["completed"]) - 1
        total = len(plan["planned"]) - 1
        self.tree_stage_label.setText(
            f"Ручной билд · уровень {level} · {used}/{total} · дальше: {first_name}"
        )
        focus_key = (level, str(first or ""))
        if first and focus_key != self._manual_focus_key:
            self._manual_focus_key = focus_key
            QTimer.singleShot(0, self.tree_canvas.fit_upcoming)


class ExactManualOverlay(previous.EditableBuildOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = ExactManualBuildDialog(self)
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
    window = ExactManualOverlay()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
