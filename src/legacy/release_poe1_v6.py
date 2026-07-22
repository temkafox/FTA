"""Current release with explicit completed/next leveling route."""

from __future__ import annotations

import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication, QLabel

import main as legacy
import release_poe1_v5 as previous
from poe1_stage_logic import previous_stage
from poe1_target_widgets import leveling_stage
from poe1_tree_fast import ConstructionTreePlaceholder as LevelingRouteTreeCanvas


class RouteBuildDialog(previous.OrbitalBuildDialog):
    def __init__(self, overlay):
        self._v6_ready = False
        super().__init__(overlay)
        old_canvas = self.tree_canvas
        layout = old_canvas.parentWidget().layout()
        index = layout.indexOf(old_canvas)
        selected_masteries = dict(old_canvas.selected_masteries)
        layout.removeWidget(old_canvas)
        old_canvas.deleteLater()
        self.tree_canvas = LevelingRouteTreeCanvas()
        self.tree_canvas.selected_masteries = selected_masteries
        layout.insertWidget(index, self.tree_canvas, 1)
        for label in self.tabs.widget(1).findChildren(QLabel):
            if "Зелёная рамка" in label.text() or "Зелёная" in label.text():
                label.setText(
                    "Золотое — уже взято · зелёное — маршрут текущего этапа · "
                    "двойная светлая рамка — следующий доступный узел"
                )
        self._tree_initialized = False
        self._v6_ready = True
        self.reload()

    def _render_tree(self, build, level):
        if not self._v6_ready:
            return super()._render_tree(build, level)
        super()._render_tree(build, level)
        if not build:
            return
        trees = build.get("trees", [])
        stage = leveling_stage(trees, level)
        previous_stage_data = previous_stage(trees, stage) if stage else None
        if stage:
            self.tree_canvas.set_stage(
                stage.get("nodes", []),
                previous_stage_data.get("nodes", []) if previous_stage_data else [],
            )
            self.tree_canvas.set_masteries(stage.get("masteries", ""))
            names = sorted({
                self.tree_canvas.nodes.get(node_id, {}).get("name", "Пассив")
                for node_id in self.tree_canvas.next_nodes
            })
            next_text = ", ".join(names[:4]) or "нет"
            self.tree_stage_label.setText(
                f"Уровень {level} · {stage.get('title', 'Дерево')} · "
                f"взято {len(self.tree_canvas.completed_nodes)} · "
                f"маршрут +{len(self.tree_canvas.route_nodes)} · далее: {next_text}"
            )


class RouteOverlay(previous.OrbitalOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = RouteBuildDialog(self)
            self._build_dialog.finished.connect(lambda _: setattr(self, "_build_dialog", None))
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
    window = RouteOverlay()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
