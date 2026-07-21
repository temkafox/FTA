"""Tightly dock the compact chronological mini-tree beside the overlay."""

from __future__ import annotations

from PyQt5.QtCore import QPoint
from PyQt5.QtWidgets import QApplication

import release_poe1_v51 as mini_release
from poe1_mini_tree_v4 import MiniPassiveRoute
from release_poe1_v54 import MiniTreeOverlay as BaseMiniTreeOverlay


mini_release.MiniPassiveRoute = MiniPassiveRoute


class MiniTreeOverlay(BaseMiniTreeOverlay):
    def __init__(self):
        super().__init__()
        self.mini_tree.setFixedSize(88, 38)
        self._mini_panel.setFixedSize(88, 38)
        self._position_mini_panel()

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

