"""Small passive preview nodes with a name-only hover tooltip."""

from __future__ import annotations

import math

from PyQt5.QtWidgets import QToolTip

from poe1_mini_tree_v2 import MiniPassiveRoute as BaseMiniPassiveRoute


class MiniPassiveRoute(BaseMiniPassiveRoute):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(56)
        self.setMouseTracking(True)
        self._hit_centers = {}
        self._hovered_node = None
        self.setStyleSheet("""
            QToolTip {
                color: #eadfca;
                background: #080806;
                border: 1px solid #8a6937;
                padding: 4px 7px;
            }
        """)

    def _node_size(self, node_id):
        node = self._node(node_id)
        if node.get("isKeystone"):
            return 28.0
        if node.get("isNotable") or node.get("isMastery"):
            return 25.0
        if node.get("classStartIndex") is not None:
            return 27.0
        return 21.0

    def paintEvent(self, event):
        self._hit_centers = self._screen_positions()
        super().paintEvent(event)

    def mouseMoveEvent(self, event):
        nearest = None
        distance = float("inf")
        for node_id, center in self._hit_centers.items():
            current = math.hypot(event.x() - center.x(), event.y() - center.y())
            limit = self._node_size(node_id) / 2.0 + 5.0
            if current <= limit and current < distance:
                nearest, distance = node_id, current
        if nearest != self._hovered_node:
            self._hovered_node = nearest
            if nearest:
                QToolTip.showText(
                    event.globalPos(),
                    str(self._node(nearest).get("name") or "Passive Skill"),
                    self,
                )
            else:
                QToolTip.hideText()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self._hovered_node = None
        QToolTip.hideText()
        super().leaveEvent(event)

