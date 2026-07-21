"""PoE 1 release: nearest connected route, Russian bodies, overlay styling."""

from __future__ import annotations

import sys

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication

import main as legacy
import release_poe1_v26 as previous
from poe1_gem_widgets_v6 import RussianOverlayGemChains
from poe1_level_plan_v10 import nearest_connected_plan
from poe1_tree_renderer_v15 import RussianDescriptionTreeCanvas
from release_poe1_v8 import TREE_GRAPH


class LocalizedOverlayBuildDialog(previous.RestoredAscendancyBuildDialog):
    def __init__(self, overlay):
        self._v27_ready = False
        super().__init__(overlay)

        old_gems = self.gem_links
        gem_layout = old_gems.parentWidget().layout()
        gem_index = gem_layout.indexOf(old_gems)
        gem_layout.removeWidget(old_gems)
        old_gems.deleteLater()
        self.gem_links = RussianOverlayGemChains()
        self.gem_links.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        gem_layout.insertWidget(gem_index, self.gem_links, 1)

        old_tree = self.tree_canvas
        tree_layout = old_tree.parentWidget().layout()
        tree_index = tree_layout.indexOf(old_tree)
        selected_masteries = dict(old_tree.selected_masteries)
        tree_layout.removeWidget(old_tree)
        old_tree.deleteLater()
        self.tree_canvas = RussianDescriptionTreeCanvas()
        self.tree_canvas.selected_masteries = selected_masteries
        tree_layout.insertWidget(tree_index, self.tree_canvas, 1)
        try:
            self.ascendancy_button.clicked.disconnect()
        except TypeError:
            pass
        self.ascendancy_button.clicked.connect(self.tree_canvas.fit_ascendancy)

        self._apply_overlay_style()
        self._tree_initialized = False
        self._focused_stage_key = None
        self._v27_ready = True
        self.reload()

    def _apply_overlay_style(self):
        style = legacy.Style
        self.setStyleSheet(f"""
            QDialog, QWidget {{ background:{style.BG}; color:{style.TEXT_PRIMARY}; }}
            QLabel {{ color:{style.TEXT_PRIMARY}; background:transparent; }}
            QComboBox {{ background:{style.BG_SECONDARY}; color:{style.TEXT_PRIMARY};
                border:1px solid {style.BORDER}; border-radius:{style.RAD_S}px; padding:7px 10px; }}
            QPushButton {{ background:{style.BG_SECONDARY}; color:{style.TEXT_SECONDARY};
                border:1px solid {style.BORDER}; border-radius:{style.RAD_S}px; padding:7px 11px; }}
            QPushButton:hover {{ color:{style.TEXT_PRIMARY}; border-color:{style.ACCENT}; background:{style.HOVER}; }}
            QPushButton:pressed {{ color:{style.BG}; background:{style.ACCENT}; }}
            QPushButton:disabled {{ color:{style.TEXT_DISABLED}; }}
            QScrollArea {{ background:transparent; border:0; }}
            QScrollBar:vertical {{ background:{style.BG}; width:10px; }}
            QScrollBar::handle:vertical {{ background:{style.BG_SECONDARY}; border-radius:5px; min-height:24px; }}
            QSplitter::handle {{ background:{style.BORDER}; }}
            QFrame {{ border-color:{style.BORDER}; }}
        """)
        self.tree_stage_label.setStyleSheet(f"color:{style.ACCENT}; font-weight:600;")
        self.status.setStyleSheet(f"color:{style.TEXT_MUTED};")
        self.gem_links.body.setStyleSheet(f"background:{style.BG};")

    def _render_tree(self, build, level):
        if not self._v27_ready:
            return super()._render_tree(build, level)
        if not build:
            self.tree_stage_label.setText("Импортируйте PoB")
            self.tree_canvas.set_quest_progression([], [], [], {}, {})
            self.tree_canvas.set_ascendancy_build(None, level)
            return
        plan = nearest_connected_plan(
            build.get("trees", []), level, TREE_GRAPH,
            self.tree_canvas.positions, self.tree_canvas.nodes,
        )
        target = plan.get("target")
        if not target:
            self.tree_stage_label.setText("Дерево в PoB не найдено")
            self.tree_canvas.set_quest_progression([], [], [], {}, {})
            self.tree_canvas.set_ascendancy_build(build, level)
            return
        old_center, old_scale = self.tree_canvas.center, self.tree_canvas.scale
        self.tree_canvas.set_quest_progression(
            plan["planned"], plan["completed"], plan["upcoming"],
            plan["node_levels"], {},
        )
        self.tree_canvas.set_masteries(target.get("masteries", ""))
        self.tree_canvas.set_ascendancy_build(build, level)
        self.ascendancy_button.setEnabled(bool(self.tree_canvas.ascendancy.get("nodes")))
        if self._tree_initialized:
            self.tree_canvas.center, self.tree_canvas.scale = old_center, old_scale
            self.tree_canvas.update()
        else:
            self._tree_initialized = True
        first = plan["upcoming"][0] if plan["upcoming"] else None
        first_key = str(first) if first is not None else ""
        first_name = self.tree_canvas.nodes.get(first_key, {}).get("name", "Passive") if first else "этап завершён"
        self.tree_stage_label.setText(
            f"Уровень персонажа {level} · следующая нода: {first_name}"
        )
        focus_key = (level, first_key)
        if focus_key != self._focused_stage_key:
            self._focused_stage_key = focus_key
            QTimer.singleShot(0, self._fit_upcoming)


class LocalizedOverlay(previous.RestoredAscendancyOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = LocalizedOverlayBuildDialog(self)
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
    window = LocalizedOverlay()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
