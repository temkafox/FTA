"""Immediate-focus tree with distinct labels for level and quest passives."""

from PyQt5.QtCore import QRectF, Qt
from PyQt5.QtGui import QColor, QFont, QPainter, QPen

from poe1_tree_renderer_v9 import ImmediateFocusTreeCanvas


class QuestAwareTreeCanvas(ImmediateFocusTreeCanvas):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.node_markers = {}

    def set_quest_progression(self, planned, completed, upcoming, node_levels, node_markers):
        super().set_level_progression(planned, completed, upcoming, node_levels)
        self.node_markers = {str(node): str(value) for node, value in node_markers.items()}
        # Suppress the numeric badge from the parent; this renderer draws the
        # more explicit level/quest/bandit marker below.
        self.node_levels = {}
        self.update()

    def _draw_route_node(self, painter, node_id):
        super()._draw_route_node(painter, node_id)
        marker = self.node_markers.get(node_id)
        point = self.positions.get(node_id)
        if node_id not in self.route_nodes or marker is None or point is None:
            return
        screen = self._screen(point)
        size = self._node_size(self.nodes.get(node_id, {}))
        target = QRectF(screen.x() - size / 2, screen.y() - size / 2, size, size)
        width = max(16, 7 * len(marker) + 7)
        badge = QRectF(target.right() - 3, target.top() - 8, width, 15)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor("#2a1b02"), 1))
        painter.setBrush(QColor("#ffe291"))
        painter.drawRoundedRect(badge, 6, 6)
        painter.setPen(QColor("#171003"))
        painter.setFont(QFont("Segoe UI", 7, QFont.Bold))
        painter.drawText(badge, Qt.AlignCenter, marker)
