"""Dock a dynamically sized, tree-positioned passive preview."""

from __future__ import annotations

from PyQt5.QtCore import QPoint
from PyQt5.QtWidgets import QApplication

import release_poe1_v51 as mini_release
from poe1_mini_tree_v5 import MiniPassiveRoute
from release_poe1_v55 import MiniTreeOverlay as BaseMiniTreeOverlay


class MiniTreeOverlay(BaseMiniTreeOverlay):
    def __init__(self):
        super().__init__()
        self._resize_mini_panel()

    def _resize_mini_panel(self):
        if self._mini_panel is None:
            return
        size = self.mini_tree.size()
        self._mini_panel.setFixedSize(size)
        self._position_mini_panel()

    def _refresh_mini_tree(self, force=False):
        super()._refresh_mini_tree(force)
        if self._mini_panel is not None:
            self._resize_mini_panel()

    def _position_mini_panel(self):
        if self._mini_panel is None:
            return
        gap = 2
        x = self.frameGeometry().right() + gap
        y = self.y() + max(self.header.height(), 54)
        screen = QApplication.screenAt(self.frameGeometry().center())
        geometry = screen.availableGeometry() if screen else QApplication.primaryScreen().availableGeometry()
        if x + self._mini_panel.width() > geometry.right():
            x = self.x() - self._mini_panel.width() - gap
        y = max(geometry.top(), min(y, geometry.bottom() - self._mini_panel.height()))
        self._mini_panel.move(QPoint(x, y))

