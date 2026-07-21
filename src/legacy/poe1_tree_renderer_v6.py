"""Leveling-route renderer: completed path, future route and next frontier nodes."""

from __future__ import annotations

from PyQt5.QtCore import QRectF, Qt
from PyQt5.QtGui import QColor, QPainter, QPainterPath, QPen

from poe1_tree_renderer_v5 import OrbitalPassiveTreeCanvas


class LevelingRouteTreeCanvas(OrbitalPassiveTreeCanvas):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.completed_nodes = set()
        self.route_nodes = set()
        self.next_nodes = set()

    def set_stage(self, nodes, previous_nodes=None):
        super().set_stage(nodes, previous_nodes)
        target = set(self.selected)
        previous = {str(node) for node in (previous_nodes or []) if str(node) in target}
        if not previous:
            previous = {
                node_id for node_id in target
                if self.nodes.get(node_id, {}).get("classStartIndex") is not None
            }
        self.completed_nodes = previous
        self.route_nodes = target - previous
        adjacency = {node_id: set() for node_id in target}
        for first, second in self.edges:
            if first in target and second in target:
                adjacency[first].add(second)
                adjacency[second].add(first)
        self.next_nodes = {
            node_id for node_id in self.route_nodes
            if adjacency.get(node_id, set()) & self.completed_nodes
        }
        if not self.next_nodes and self.route_nodes:
            self.next_nodes = {next(iter(self.route_nodes))}
        self.update()

    def _draw_route_node(self, painter, node_id):
        node = self.nodes.get(node_id, {})
        point = self.positions.get(node_id)
        if point is None:
            return
        screen = self._screen(point)
        if not self.rect().adjusted(-25, -25, 25, 25).contains(screen.toPoint()):
            return
        size = self._node_size(node)
        target_rect = QRectF(screen.x() - size / 2, screen.y() - size / 2, size, size)
        active = node_id in self.selected
        icon_key = node.get("icon", "")
        coords = self.sprite_coords["active" if active else "inactive"].get(icon_key)
        sprite = self.active_sprite if active else self.inactive_sprite
        if coords and not sprite.isNull() and size >= 4.0:
            source = QRectF(coords["x"], coords["y"], coords["w"], coords["h"])
            clip = QPainterPath()
            clip.addEllipse(target_rect)
            painter.save()
            painter.setClipPath(clip)
            painter.setOpacity(1.0 if active else 0.42)
            painter.drawPixmap(target_rect, sprite, source)
            painter.restore()
        else:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#182035") if active else QColor("#17171b"))
            painter.drawEllipse(target_rect)

        if node_id in self.next_nodes:
            border, width, padding = QColor("#efffc1"), 2.4, 2.5
        elif node_id in self.route_nodes:
            border, width, padding = QColor("#27d94e"), 1.35, 1.0
        elif node_id in self.completed_nodes:
            border, width, padding = QColor("#e5c16f"), 1.55, 1.0
        else:
            border, width, padding = QColor(112, 91, 54, 155), 0.7, 1.0
        painter.setOpacity(1.0)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(border, width))
        painter.drawEllipse(target_rect.adjusted(-padding, -padding, padding, padding))
        if node_id in self.next_nodes:
            painter.setPen(QPen(QColor("#2af05a"), 1.2))
            painter.drawEllipse(target_rect.adjusted(-5, -5, 5, 5))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.fillRect(self.rect(), QColor("#07080a"))
        if not self.positions:
            painter.setPen(QColor("#aaa"))
            painter.drawText(self.rect(), Qt.AlignCenter, "Данные дерева не найдены")
            return
        visible_rect = self.rect().adjusted(-20, -20, 20, 20)
        painter.setPen(QPen(QColor(83, 70, 47, 95), 0.65))
        for first, second in self.edges:
            a, b = self._screen(self.positions[first]), self._screen(self.positions[second])
            if visible_rect.contains(a.toPoint()) or visible_rect.contains(b.toPoint()):
                painter.drawPath(self._edge_path(first, second))
        painter.setPen(QPen(QColor("#d8bd72"), 1.65))
        for first, second in self.edges:
            if first in self.completed_nodes and second in self.completed_nodes:
                painter.drawPath(self._edge_path(first, second))
        painter.setPen(QPen(QColor("#22db4d"), 1.75))
        for first, second in self.edges:
            if (
                first in self.selected and second in self.selected
                and (first in self.route_nodes or second in self.route_nodes)
            ):
                painter.drawPath(self._edge_path(first, second))
        for node_id in self.positions:
            self._draw_route_node(painter, node_id)
