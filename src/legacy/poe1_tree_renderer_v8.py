"""Tree renderer: green allocated nodes and gold future nodes labelled by level."""

from __future__ import annotations

from PyQt5.QtCore import QRectF, Qt
from PyQt5.QtGui import QColor, QFont, QPainter, QPainterPath, QPen

from poe1_tree_renderer_v7 import ProgressionTreeCanvas


class LevelMappedTreeCanvas(ProgressionTreeCanvas):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.node_levels = {}

    def set_level_progression(self, planned, completed, upcoming, node_levels):
        super().set_progression(planned, completed, upcoming)
        self.node_levels = {str(node): int(value) for node, value in node_levels.items()}
        self.preview_nodes = set(self.upcoming_order)
        self.next_nodes = set(self.upcoming_order[:1])
        self.update()

    def _draw_route_node(self, painter, node_id):
        node = self.nodes.get(node_id, {})
        point = self.positions.get(node_id)
        if point is None:
            return
        screen = self._screen(point)
        if not self.rect().adjusted(-28, -28, 28, 28).contains(screen.toPoint()):
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
            painter.setOpacity(1.0 if node_id in self.completed_nodes else 0.78)
            painter.drawPixmap(target_rect, sprite, source)
            painter.restore()
        else:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#182035") if active else QColor("#17171b"))
            painter.drawEllipse(target_rect)

        if node_id in self.next_nodes:
            border, width, padding = QColor("#fff0ad"), 2.7, 3.0
        elif node_id in self.route_nodes:
            border, width, padding = QColor("#dfb84f"), 1.55, 1.2
        elif node_id in self.completed_nodes:
            border, width, padding = QColor("#32e567"), 1.8, 1.2
        else:
            border, width, padding = QColor(112, 91, 54, 155), 0.7, 1.0
        painter.setOpacity(1.0)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(border, width))
        painter.drawEllipse(target_rect.adjusted(-padding, -padding, padding, padding))

        required_level = self.node_levels.get(node_id)
        if node_id in self.route_nodes and required_level is not None:
            text = str(required_level)
            badge_width = 14 if required_level < 10 else 18
            badge = QRectF(
                target_rect.right() - 3,
                target_rect.top() - 8,
                badge_width,
                14,
            )
            painter.setPen(QPen(QColor("#241b07"), 1))
            painter.setBrush(QColor("#ffe291"))
            painter.drawRoundedRect(badge, 6, 6)
            painter.setPen(QColor("#171003"))
            painter.setFont(QFont("Segoe UI", 7, QFont.Bold))
            painter.drawText(badge, Qt.AlignCenter, text)

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

        painter.setPen(QPen(QColor("#25ce58"), 1.9))
        for first, second in self.edges:
            if first in self.completed_nodes and second in self.completed_nodes:
                painter.drawPath(self._edge_path(first, second))

        painter.setPen(QPen(QColor("#c89b36"), 1.45))
        for first, second in self.edges:
            if first in self.selected and second in self.selected and (
                first in self.route_nodes or second in self.route_nodes
            ):
                painter.drawPath(self._edge_path(first, second))

        for node_id in self.positions:
            self._draw_route_node(painter, node_id)
