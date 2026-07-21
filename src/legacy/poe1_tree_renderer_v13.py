"""Render the imported ascendancy route at its native main-tree coordinates."""

from __future__ import annotations

import math

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QColor, QPainter, QPainterPath, QPen

from poe1_ascendancy_plan import ascendancy_plan
from poe1_tree_renderer_v11 import CleanPassiveTreeCanvas


class NativeAscendancyTreeCanvas(CleanPassiveTreeCanvas):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ascendancy = {"name": "Ассенданси", "nodes": [], "edges": [], "completed": [], "next": []}

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

    def fit_ascendancy(self):
        points = [
            self.positions[node_id] for node_id in self.ascendancy.get("nodes", [])
            if node_id in self.positions
        ]
        if not points:
            return
        min_x, max_x = min(point.x() for point in points), max(point.x() for point in points)
        min_y, max_y = min(point.y() for point in points), max(point.y() for point in points)
        self.center = QPointF((min_x + max_x) / 2, (min_y + max_y) / 2)
        width, height = max(1050.0, max_x - min_x), max(900.0, max_y - min_y)
        self.scale = min(
            max(0.04, (self.width() - 90) / width),
            max(0.04, (self.height() - 90) / height),
            0.38,
        )
        self.update()

    def _draw_ascendancy_node(self, painter, node_id):
        point = self.positions.get(node_id)
        if point is None:
            return
        screen = self._screen(point)
        if not self.rect().adjusted(-30, -30, 30, 30).contains(screen.toPoint()):
            return
        node = self.nodes.get(node_id, {})
        size = max(8.0, self._node_size(node))
        if node.get("isAscendancyStart"):
            size *= 1.55
        target = QRectF(screen.x() - size / 2, screen.y() - size / 2, size, size)
        completed = node_id in set(self.ascendancy.get("completed", []))
        next_node = node_id in set(self.ascendancy.get("next", []))
        icon_key = node.get("icon", "")
        coords = self.sprite_coords["active" if completed else "inactive"].get(icon_key)
        sprite = self.active_sprite if completed else self.inactive_sprite
        if coords and not sprite.isNull():
            source = QRectF(coords["x"], coords["y"], coords["w"], coords["h"])
            clip = QPainterPath()
            clip.addEllipse(target)
            painter.save()
            painter.setClipPath(clip)
            painter.setOpacity(1.0 if completed else 0.78)
            painter.drawPixmap(target, sprite, source)
            painter.restore()
        else:
            painter.setBrush(QColor("#123b24") if completed else QColor("#3b2b0f"))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(target)
        border = QColor("#39f072") if completed else QColor("#e1ae35")
        if next_node:
            border = QColor("#f4ffe8")
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(border, 2.7 if next_node else 1.8))
        painter.drawEllipse(target.adjusted(-2, -2, 2, 2))

    def _paint_native_ascendancy(self, painter):
        route = set(self.ascendancy.get("nodes", []))
        if not route:
            return
        completed = set(self.ascendancy.get("completed", []))
        painter.setPen(QPen(QColor("#d3a326"), 2.0))
        for first, second in self.ascendancy.get("edges", []):
            if first in self.positions and second in self.positions:
                painter.drawLine(self._screen(self.positions[first]), self._screen(self.positions[second]))
        painter.setPen(QPen(QColor("#28e562"), 2.5))
        for first, second in self.ascendancy.get("edges", []):
            if first in completed and second in completed:
                painter.drawLine(self._screen(self.positions[first]), self._screen(self.positions[second]))
        for node_id in route:
            self._draw_ascendancy_node(painter, node_id)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        self._paint_native_ascendancy(painter)

    def _asc_node_at(self, event):
        nearest, limit = None, 13.0
        route = set(self.ascendancy.get("nodes", []))
        for node_id in route:
            point = self.positions.get(node_id)
            if point is None:
                continue
            screen = self._screen(point)
            radius = max(7.0, self._node_size(self.nodes.get(node_id, {})) / 2 + 4)
            distance = math.hypot(screen.x() - event.x(), screen.y() - event.y())
            if distance < min(limit, radius):
                nearest, limit = node_id, distance
        return nearest

    def mouseMoveEvent(self, event):
        node_id = self._asc_node_at(event)
        if node_id:
            self.node_tooltip.show_node(
                self.nodes.get(node_id, {}),
                node_id in set(self.ascendancy.get("completed", [])),
                event.globalPos(),
            )
            return
        super().mouseMoveEvent(event)
