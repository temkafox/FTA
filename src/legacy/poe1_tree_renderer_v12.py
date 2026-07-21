"""Main passive canvas with an integrated, non-centering ascendancy inset."""

from __future__ import annotations

import math

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QColor, QFont, QPainter, QPen

from poe1_ascendancy_plan import ascendancy_plan
from poe1_tree_renderer_v11 import CleanPassiveTreeCanvas


class IntegratedAscendancyTreeCanvas(CleanPassiveTreeCanvas):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ascendancy = {"name": "Ассенданси", "nodes": [], "edges": [], "completed": [], "next": []}
        self._asc_screen = {}
        self._asc_panel = QRectF()

    def set_ascendancy_build(self, build, level):
        if not build:
            self.ascendancy = {"name": "Ассенданси", "nodes": [], "edges": [], "completed": [], "next": []}
        else:
            plan = ascendancy_plan(
                build.get("trees", []), self.nodes,
                build.get("ascendancy", ""), level,
            )
            route = list(plan.get("nodes", []))
            completed = list(plan.get("completed", []))
            if route and route[0] not in completed:
                completed.insert(0, route[0])
            plan["completed"] = completed
            self.ascendancy = plan
        self.update()

    def _ascendancy_layout(self):
        panel_width = max(210.0, min(310.0, self.width() * 0.37))
        panel_height = max(205.0, min(300.0, self.height() * 0.48))
        self._asc_panel = QRectF(
            self.width() - panel_width - 12, 12, panel_width, panel_height
        )
        ids = [node_id for node_id in self.ascendancy.get("nodes", []) if node_id in self.positions]
        if not ids:
            self._asc_screen = {}
            return
        xs = [self.positions[node_id].x() for node_id in ids]
        ys = [self.positions[node_id].y() for node_id in ids]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        width, height = max(1.0, max_x - min_x), max(1.0, max_y - min_y)
        content = self._asc_panel.adjusted(35, 38, -35, -38)
        scale = min(content.width() / width, content.height() / height)
        used_w, used_h = width * scale, height * scale
        left = content.left() + (content.width() - used_w) / 2
        top = content.top() + (content.height() - used_h) / 2
        self._asc_screen = {
            node_id: QPointF(
                left + (self.positions[node_id].x() - min_x) * scale,
                top + (self.positions[node_id].y() - min_y) * scale,
            )
            for node_id in ids
        }

    def _paint_ascendancy(self, painter):
        self._ascendancy_layout()
        if not self._asc_screen:
            return
        painter.save()
        painter.setOpacity(0.97)
        painter.setPen(QPen(QColor("#80643c"), 1.4))
        painter.setBrush(QColor("#060709"))
        painter.drawRoundedRect(self._asc_panel, 4, 4)
        painter.setOpacity(1.0)
        painter.setPen(QColor("#e2c47f"))
        painter.setFont(QFont("Georgia", 11, QFont.DemiBold))
        painter.drawText(
            self._asc_panel.adjusted(8, 5, -8, 0),
            Qt.AlignTop | Qt.AlignHCenter,
            self.ascendancy.get("name", "Ассенданси"),
        )

        completed = set(self.ascendancy.get("completed", []))
        next_nodes = set(self.ascendancy.get("next", []))
        painter.setPen(QPen(QColor("#c89525"), 2.0))
        for first, second in self.ascendancy.get("edges", []):
            if first in self._asc_screen and second in self._asc_screen:
                painter.drawLine(self._asc_screen[first], self._asc_screen[second])
        painter.setPen(QPen(QColor("#28e562"), 2.5))
        for first, second in self.ascendancy.get("edges", []):
            if first in self._asc_screen and second in self._asc_screen:
                if first in completed and second in completed:
                    painter.drawLine(self._asc_screen[first], self._asc_screen[second])

        for node_id, point in self._asc_screen.items():
            node = self.nodes.get(node_id, {})
            radius = 16 if node.get("isAscendancyStart") else (13 if node.get("isNotable") else 9)
            if node_id in completed:
                border, fill = QColor("#39f072"), QColor("#123b24")
            else:
                border, fill = QColor("#e1ae35"), QColor("#3b2b0f")
            if node_id in next_nodes:
                border = QColor("#f4ffe8")
            painter.setPen(QPen(border, 2.8 if node_id in next_nodes else 1.8))
            painter.setBrush(fill)
            painter.drawEllipse(point, radius, radius)
            painter.setPen(QColor("#f0eadc"))
            painter.setFont(QFont("Georgia", 7, QFont.Bold))
            painter.drawText(
                QRectF(point.x()-radius, point.y()-radius, radius*2, radius*2),
                Qt.AlignCenter,
                (node.get("name") or "?")[:1].upper(),
            )
        painter.restore()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        self._paint_ascendancy(painter)

    def _asc_node_at(self, position):
        nearest, distance_limit = None, 19.0
        for node_id, point in self._asc_screen.items():
            distance = math.hypot(point.x() - position.x(), point.y() - position.y())
            if distance < distance_limit:
                nearest, distance_limit = node_id, distance
        return nearest

    def mouseMoveEvent(self, event):
        node_id = self._asc_node_at(event.pos())
        if node_id:
            self.node_tooltip.show_node(
                self.nodes.get(node_id, {}),
                node_id in set(self.ascendancy.get("completed", [])),
                event.globalPos(),
            )
            return
        super().mouseMoveEvent(event)
