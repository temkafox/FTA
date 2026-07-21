"""Passive tree renderer with a numbered, level-aware upcoming route."""

from __future__ import annotations

from PyQt5.QtCore import QRectF, Qt
from PyQt5.QtGui import QColor, QFont, QPainter, QPainterPath, QPen

from poe1_combined_widgets import FocusedLevelingTreeCanvas


class ProgressionTreeCanvas(FocusedLevelingTreeCanvas):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.upcoming_order = []
        self.preview_nodes = set()

    def set_progression(self, planned, completed, upcoming):
        super().set_stage(planned, completed)
        route = set(self.route_nodes)
        self.upcoming_order = [str(node) for node in upcoming if str(node) in route]
        self.preview_nodes = set(self.upcoming_order[:5])
        self.next_nodes = set(self.upcoming_order[:1])
        self.update()

    def upcoming_nodes(self, limit=10):
        focus = set(self.upcoming_order[:limit])
        if not focus:
            focus = set(self.completed_nodes)
        return focus

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
            painter.setOpacity(1.0 if node_id in self.completed_nodes or node_id in self.preview_nodes else 0.58)
            painter.drawPixmap(target_rect, sprite, source)
            painter.restore()
        else:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#182035") if active else QColor("#17171b"))
            painter.drawEllipse(target_rect)

        if node_id in self.next_nodes:
            border, width, padding = QColor("#f5ffe0"), 2.6, 3.0
        elif node_id in self.preview_nodes:
            border, width, padding = QColor("#37e867"), 1.8, 1.6
        elif node_id in self.route_nodes:
            border, width, padding = QColor("#176f38"), 1.0, 1.0
        elif node_id in self.completed_nodes:
            border, width, padding = QColor("#e5c16f"), 1.55, 1.0
        else:
            border, width, padding = QColor(112, 91, 54, 155), 0.7, 1.0
        painter.setOpacity(1.0)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(border, width))
        painter.drawEllipse(target_rect.adjusted(-padding, -padding, padding, padding))

        if node_id in self.preview_nodes:
            number = self.upcoming_order.index(node_id) + 1
            badge_size = 13
            badge = QRectF(
                target_rect.right() - 3,
                target_rect.top() - 7,
                badge_size,
                badge_size,
            )
            painter.setPen(QPen(QColor("#0b160d"), 1))
            painter.setBrush(QColor("#e8ffd9") if number == 1 else QColor("#38df65"))
            painter.drawEllipse(badge)
            painter.setPen(QColor("#071108"))
            painter.setFont(QFont("Segoe UI", 7, QFont.Bold))
            painter.drawText(badge, Qt.AlignCenter, str(number))

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

        painter.setPen(QPen(QColor("#155a2d"), 1.05))
        for first, second in self.edges:
            if first in self.selected and second in self.selected and (
                first in self.route_nodes or second in self.route_nodes
            ):
                painter.drawPath(self._edge_path(first, second))

        highlighted = self.completed_nodes | self.preview_nodes
        painter.setPen(QPen(QColor("#31e761"), 2.15))
        for first, second in self.edges:
            if first in highlighted and second in highlighted and (
                first in self.preview_nodes or second in self.preview_nodes
            ):
                painter.drawPath(self._edge_path(first, second))

        for node_id in self.positions:
            self._draw_route_node(painter, node_id)
