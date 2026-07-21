"""Collision-free mini route using the passive tree's real coordinates."""

from __future__ import annotations

import math

from PyQt5.QtCore import QPointF

from poe1_mini_tree_v4 import MiniPassiveRoute as BaseMiniPassiveRoute


class MiniPassiveRoute(BaseMiniPassiveRoute):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._layout_positions = {}

    def set_build_level(self, build, level):
        super().set_build_level(build, level)
        self._build_tree_layout()
        self.update()

    def _build_tree_layout(self):
        nodes = list(self._visible_nodes)
        if not nodes:
            self._layout_positions = {}
            self.setFixedSize(1, 1)
            return

        margin = 5.0
        scale = 0.01
        # Find one uniform scale that preserves the official tree geometry and
        # guarantees a visible gap between every pair of node frames.
        for index, first in enumerate(nodes):
            a = self._positions[first]
            for second in nodes[index + 1 :]:
                b = self._positions[second]
                distance = math.hypot(a.x() - b.x(), a.y() - b.y())
                if distance <= 0.001:
                    continue
                required = (
                    self._node_size(first) / 2.0
                    + self._node_size(second) / 2.0
                    + 7.0
                )
                scale = max(scale, required / distance)

        raw = {
            node: QPointF(
                self._positions[node].x() * scale,
                self._positions[node].y() * scale,
            )
            for node in nodes
        }
        min_x = min(
            raw[node].x() - self._node_size(node) / 2.0 for node in nodes
        )
        max_x = max(
            raw[node].x() + self._node_size(node) / 2.0 for node in nodes
        )
        min_y = min(
            raw[node].y() - self._node_size(node) / 2.0 for node in nodes
        )
        max_y = max(
            raw[node].y() + self._node_size(node) / 2.0 for node in nodes
        )
        self._layout_positions = {
            node: QPointF(
                point.x() - min_x + margin,
                point.y() - min_y + margin,
            )
            for node, point in raw.items()
        }
        self.setFixedSize(
            max(26, int(math.ceil(max_x - min_x + margin * 2))),
            max(26, int(math.ceil(max_y - min_y + margin * 2))),
        )

    def _screen_positions(self):
        return dict(self._layout_positions)

