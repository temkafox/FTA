"""PoE 1 release with compact gem links and a focused tree in one view."""

from __future__ import annotations

import sys

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

import main as legacy
import main_poe1 as base
import release_poe1_v6 as previous
from poe1_combined_widgets import CompactGemChains
from poe1_tree_fast import ConstructionTreePlaceholder as FocusedLevelingTreeCanvas
from poe1_target_widgets import leveling_stage


class CombinedBuildDialog(previous.RouteBuildDialog):
    def __init__(self, overlay):
        self._v7_ready = False
        self._focused_stage_key = None
        super().__init__(overlay)

        root = self.layout()
        tab_index = root.indexOf(self.tabs)
        root.removeWidget(self.tabs)
        self.tabs.hide()

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(2)
        splitter.setStyleSheet(
            "QSplitter::handle{background:#2b2d33;}"
            "QScrollBar{background:#111216;}"
        )

        gem_page = QWidget()
        gem_page.setMinimumWidth(300)
        gem_page.setStyleSheet("background:#08090b;")
        gem_layout = QVBoxLayout(gem_page)
        gem_layout.setContentsMargins(0, 0, 0, 0)
        gem_layout.setSpacing(0)
        self.gem_links = CompactGemChains()
        self.gem_links.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        gem_layout.addWidget(self.gem_links, 1)

        tree_page = QWidget()
        tree_page.setMinimumWidth(520)
        tree_page.setStyleSheet("background:#08090b;")
        tree_layout = QVBoxLayout(tree_page)
        tree_layout.setContentsMargins(8, 8, 8, 8)
        tree_layout.setSpacing(7)

        tree_head = QHBoxLayout()
        self.tree_stage_label = QLabel()
        self.tree_stage_label.setStyleSheet("color:#e6c477;")
        self.tree_stage_label.setWordWrap(True)
        tree_head.addWidget(self.tree_stage_label, 1)

        near_btn = QPushButton("К ближайшим")
        near_btn.setStyleSheet(base.button_style())
        near_btn.clicked.connect(self._fit_upcoming)
        selected_btn = QPushButton("К выбранным")
        selected_btn.setStyleSheet(base.button_style())
        selected_btn.clicked.connect(self._fit_selected)
        all_btn = QPushButton("Всё дерево")
        all_btn.setStyleSheet(base.button_style())
        all_btn.clicked.connect(self._fit_all)
        tree_head.addWidget(near_btn)
        tree_head.addWidget(selected_btn)
        tree_head.addWidget(all_btn)
        tree_layout.addLayout(tree_head)

        self.tree_canvas = FocusedLevelingTreeCanvas()
        tree_layout.addWidget(self.tree_canvas, 1)
        legend = QLabel(
            "Золотое — уже взято · зелёное — текущий маршрут · "
            "двойная светлая рамка — следующий доступный узел"
        )
        legend.setStyleSheet("color:#777;")
        legend.setWordWrap(True)
        tree_layout.addWidget(legend)

        splitter.addWidget(gem_page)
        splitter.addWidget(tree_page)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([390, 790])
        root.insertWidget(max(0, tab_index), splitter, 1)
        self.combined_splitter = splitter

        self.resize(1220, 760)
        self._tree_initialized = False
        self._v7_ready = True
        self.reload()

    def _render_gems(self, build, level):
        if not self._v7_ready:
            return super()._render_gems(build, level)
        if not build:
            self.gem_links.set_links("Импортируйте PoB", [])
            return
        stage = leveling_stage(build.get("gem_sets", []), level)
        if not stage:
            self.gem_links.set_links("Связки не найдены", [])
            return
        title = stage.get("title", "Связки")
        self.gem_links.set_links(title, stage.get("links", []))
        self.status.setText(f"Уровень персонажа {level} · набор камней «{title}»")

    def _render_tree(self, build, level):
        if not self._v7_ready:
            return super()._render_tree(build, level)

        super()._render_tree(build, level)
        if not build:
            self._focused_stage_key = None
            return
        stage = leveling_stage(build.get("trees", []), level)
        if not stage:
            self._focused_stage_key = None
            return

        stage_key = (
            stage.get("level", 1),
            stage.get("title", ""),
            tuple(stage.get("nodes", [])),
        )
        if stage_key != self._focused_stage_key:
            self._focused_stage_key = stage_key
            QTimer.singleShot(0, self._fit_upcoming)

    def _fit_upcoming(self):
        if self._v7_ready:
            self.tree_canvas.fit_upcoming()


class CombinedOverlay(previous.RouteOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = CombinedBuildDialog(self)
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
    window = CombinedOverlay()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
