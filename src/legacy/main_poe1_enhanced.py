"""Enhanced PoE 1 launcher with visual tree, gem links and Client.txt sync."""

from __future__ import annotations

import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication, QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

import main as legacy
import main_poe1 as base
from poe1_builds import clamp_level, stage_for_level
from poe1_widgets import ClientLevelMonitor, GemLinksView, PassiveTreeCanvas


class EnhancedBuildProgressDialog(base.BuildProgressDialog):
    def __init__(self, overlay):
        self._enhanced_ready = False
        super().__init__(overlay)

        self.tabs.clear()
        self.gem_links = GemLinksView()
        self.tabs.addTab(self.gem_links, "Камни и связки")

        tree_page = QWidget()
        tree_layout = QVBoxLayout(tree_page)
        tree_layout.setContentsMargins(8, 8, 8, 8)
        tree_head = QHBoxLayout()
        self.tree_stage_label = QLabel()
        self.tree_stage_label.setStyleSheet("color:#e6c477;")
        tree_head.addWidget(self.tree_stage_label, 1)
        fit_selected = QPushButton("К выбранным")
        fit_selected.setStyleSheet(base.button_style())
        fit_selected.clicked.connect(self._fit_selected)
        fit_all = QPushButton("Всё дерево")
        fit_all.setStyleSheet(base.button_style())
        fit_all.clicked.connect(self._fit_all)
        tree_head.addWidget(fit_selected)
        tree_head.addWidget(fit_all)
        tree_layout.addLayout(tree_head)
        self.tree_canvas = PassiveTreeCanvas()
        tree_layout.addWidget(self.tree_canvas, 1)
        legend = QLabel("Золотые — уже взятые · зелёные — новые на текущем этапе · колесо — масштаб · мышь — перемещение")
        legend.setStyleSheet("color:#777;")
        legend.setWordWrap(True)
        tree_layout.addWidget(legend)
        self.tabs.addTab(tree_page, "Дерево")

        self.step_context = QLabel()
        self.step_context.setWordWrap(True)
        self.step_context.setStyleSheet(
            f"color:{legacy.Style.TEXT_SECONDARY}; background:{legacy.Style.BG_SECONDARY}; "
            f"border:1px solid {legacy.Style.BORDER}; border-radius:7px; padding:8px;"
        )
        self.layout().insertWidget(2, self.step_context)

        self.log_status = QLabel()
        self.log_status.setWordWrap(True)
        self.log_status.setStyleSheet("color:#6f9f77;")
        self.layout().insertWidget(self.layout().count() - 1, self.log_status)

        self.monitor = ClientLevelMonitor(self)
        self.monitor.level_seen.connect(self._on_level_seen)
        self.monitor.status_changed.connect(self.log_status.setText)
        self.overlay.content.active_step_changed.connect(self._refresh_step_context)
        self._enhanced_ready = True
        self.reload()
        self._refresh_step_context()
        self.monitor.start()

    def _render_gems(self, build, level):
        if not self._enhanced_ready:
            return super()._render_gems(build, level)
        if not build:
            self.gem_links.set_links("Импортируйте PoB", [])
            self.status.setText("У персонажа пока нет импортированного билда.")
            return
        stage = stage_for_level(build.get("gem_sets", []), level)
        if not stage:
            self.gem_links.set_links("Связки в PoB не найдены", [])
            return
        self.gem_links.set_links(stage.get("title", "Связки"), stage.get("links", []))
        self.status.setText(
            f"Связки без привязки к экипировке · этап уровня {stage.get('level', 1)}"
        )

    def _render_tree(self, build, level):
        if not self._enhanced_ready:
            return super()._render_tree(build, level)
        if not build:
            self.tree_stage_label.setText("Импортируйте PoB для отображения дерева")
            self.tree_canvas.set_stage([])
            return
        trees = build.get("trees", [])
        stage = stage_for_level(trees, level)
        if not stage:
            self.tree_stage_label.setText("В PoB дерево не найдено")
            self.tree_canvas.set_stage([])
            return
        previous_candidates = [
            item for item in trees
            if item is not stage and item.get("level", 1) < stage.get("level", 1)
        ]
        previous = max(previous_candidates, key=lambda item: item.get("level", 1)) if previous_candidates else None
        nodes = stage.get("nodes", [])
        previous_nodes = previous.get("nodes", []) if previous else []
        self.tree_stage_label.setText(
            f"{stage.get('title', 'Дерево')} · {len(nodes)} пассивов · "
            f"+{len(set(nodes) - set(previous_nodes))} с прошлого этапа"
        )
        self.tree_canvas.set_stage(nodes, previous_nodes)

    def _fit_selected(self):
        self.tree_canvas.fit_selected()
        self.tree_canvas.update()

    def _fit_all(self):
        self.tree_canvas.fit_all()

    def _refresh_step_context(self):
        act, index, text = self.overlay.content.get_active_step_info()
        if index < 0:
            self.step_context.setText("Кампания завершена")
        else:
            self.step_context.setText(
                f"Текущий шаг: {act} · #{index + 1}\n{text}"
            )

    def _on_level_seen(self, character_name, character_class, level):
        profile = self.overlay.active_profile()
        bound_name = profile.get("log_character_name", "").strip()
        profile_name = profile.get("name", "").strip()
        build = profile.get("build") or {}
        allowed_classes = {
            str(build.get("class", "")).casefold(),
            str(build.get("ascendancy", "")).casefold(),
        } - {""}
        name_matches = character_name.casefold() in {
            bound_name.casefold(), profile_name.casefold()
        } - {""}
        class_matches = character_class.casefold() in allowed_classes
        if bound_name and character_name.casefold() != bound_name.casefold():
            return
        if not bound_name and not name_matches and not class_matches:
            return
        profile["log_character_name"] = character_name
        profile["level"] = clamp_level(level)
        self.overlay.save_profiles()
        self.log_status.setText(
            f"Client.txt: {character_name} ({character_class}) · уровень {level}"
        )
        self.refresh_level()

    def _profile_changed(self, index):
        super()._profile_changed(index)
        if self._enhanced_ready:
            self._refresh_step_context()


class EnhancedPoe1Overlay(base.Poe1Overlay):
    def _interactive_widgets(self):
        widgets = super()._interactive_widgets()
        if hasattr(self, "build_btn") and self.build_btn not in widgets:
            widgets.append(self.build_btn)
        return widgets

    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = EnhancedBuildProgressDialog(self)
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
    window = EnhancedPoe1Overlay()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
