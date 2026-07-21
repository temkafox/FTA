"""Compact chronological previous/current/next passive preview."""

from __future__ import annotations

from PyQt5.QtCore import QPointF

from poe1_mini_tree_v3 import MiniPassiveRoute as BaseMiniPassiveRoute


class MiniPassiveRoute(BaseMiniPassiveRoute):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(88, 38)

    def _pick_nodes(self, completed, upcoming):
        completed = [str(node) for node in completed if str(node) in self._nodes]
        upcoming = [str(node) for node in upcoming if str(node) in self._nodes]
        chosen = []
        # Left to right: the passive just allocated, the one to allocate now,
        # and the one immediately after it in the saved leveling route.
        if completed:
            chosen.append(completed[-1])
        chosen.extend(upcoming[:2])
        if len(chosen) < 3:
            for node in reversed(completed[:-1]):
                if node not in chosen:
                    chosen.insert(0, node)
                if len(chosen) == 3:
                    break
        return chosen[-3:]

    def set_build_level(self, build, level):
        super().set_build_level(build, level)
        # Only adjacent chronological items may receive a line. A route can
        # switch branches, so never draw a shortcut across the middle node.
        self._edges = [
            (self._visible_nodes[index], self._visible_nodes[index + 1])
            for index in range(len(self._visible_nodes) - 1)
            if self._connected(
                self._visible_nodes[index], self._visible_nodes[index + 1]
            )
        ]
        self.update()

    def _screen_positions(self):
        # The real tree coordinates are intentionally not used here: nearby
        # orbit nodes otherwise overlap in a short horizontal HUD strip.
        count = len(self._visible_nodes)
        if not count:
            return {}
        spacing = 28.0
        start_x = 16.0
        return {
            node_id: QPointF(start_x + index * spacing, self.height() / 2.0)
            for index, node_id in enumerate(self._visible_nodes)
        }

    def _node_size(self, node_id):
        node = self._node(node_id)
        if node.get("isKeystone"):
            return 21.0
        if node.get("isNotable") or node.get("isMastery"):
            return 18.0
        if node.get("classStartIndex") is not None:
            return 20.0
        return 15.0

