"""Masteries rendered as standalone allocations without connecting edges."""

from __future__ import annotations

from PyQt5.QtCore import QRectF, Qt
from PyQt5.QtGui import QColor, QPainter, QPen

from poe1_tree_renderer_v17 import OfficialRussianTreeCanvas


class SeparateMasteryTreeCanvas(OfficialRussianTreeCanvas):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.mastery_ids = {
            node_id for node_id, node in self.nodes.items() if node.get("isMastery")
        }
        # Mastery is a choice unlocked by a cluster, not a travel node. Do not
        # draw even a dim structural spoke from it into the ordinary route.
        self.edges = [
            (first, second) for first, second in self.edges
            if first not in self.mastery_ids and second not in self.mastery_ids
        ]
        self.completed_masteries = set()
        self.next_mastery = None

    def set_mastery_progression(self, completed, next_node=None):
        self.completed_masteries = {str(node) for node in completed}
        self.next_mastery = str(next_node) if next_node is not None else None
        self.update()

    def _draw_route_node(self, painter, node_id):
        super()._draw_route_node(painter, node_id)
        if node_id not in self.mastery_ids:
            return
        point = self.positions.get(node_id)
        if point is None:
            return
        screen = self._screen(point)
        size = self._node_size(self.nodes.get(node_id, {}))
        rect = QRectF(screen.x() - size / 2, screen.y() - size / 2, size, size)
        if node_id in self.completed_masteries:
            color, width, padding = QColor("#32e567"), 2.2, 2.0
        elif node_id == self.next_mastery:
            color, width, padding = QColor("#fff0ad"), 2.8, 3.5
        else:
            return
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(color, width))
        painter.drawEllipse(rect.adjusted(-padding, -padding, padding, padding))
