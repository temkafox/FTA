"""Clean LOD passive-tree renderer and PoE-styled tooltip."""

from __future__ import annotations

import html
import math

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PyQt5.QtWidgets import QApplication, QFrame, QLabel, QVBoxLayout

from poe1_mastery_tree import CompleteTooltipTreeCanvas
from poe1_widgets import PassiveTreeCanvas


def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


class PoePassiveTooltip(QFrame):
    def __init__(self):
        super().__init__(None, Qt.ToolTip | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setObjectName("poePassiveTooltip")
        self.setStyleSheet("""
            QFrame#poePassiveTooltip {
                background: #050505;
                border: 2px solid #80643c;
            }
            QLabel { background: transparent; border: none; }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 10)
        layout.setSpacing(6)
        self.title = QLabel()
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setFont(QFont("Georgia", 13, QFont.DemiBold))
        self.title.setStyleSheet("color:#ded4c0; padding:2px 8px 6px 8px; border-bottom:1px solid #80643c;")
        layout.addWidget(self.title)
        self.kind = QLabel()
        self.kind.setAlignment(Qt.AlignCenter)
        self.kind.setFont(QFont("Segoe UI", 9))
        self.kind.setStyleSheet("color:#9b8a6e;")
        layout.addWidget(self.kind)
        self.stats = QLabel()
        self.stats.setTextFormat(Qt.RichText)
        self.stats.setWordWrap(True)
        self.stats.setMaximumWidth(390)
        self.stats.setFont(QFont("Georgia", 11))
        self.stats.setStyleSheet("color:#8ca5ff;")
        layout.addWidget(self.stats)

    def show_node(self, node: dict, selected: bool, global_pos):
        self.title.setText(node.get("name") or "Пассивное умение")
        if node.get("isMastery"):
            kind = "МАСТЕРСТВО — ОДИН ЭФФЕКТ НА ВЫБОР"
            values = [
                "• " + " / ".join(str(value) for value in effect.get("stats", []))
                for effect in node.get("masteryEffects", [])
            ]
        else:
            kind = "КЛЮЧЕВОЕ УМЕНИЕ" if node.get("isKeystone") else (
                "ЗНАЧИМОЕ УМЕНИЕ" if node.get("isNotable") else "ПАССИВНОЕ УМЕНИЕ"
            )
            values = list(node.get("stats") or [])
        if selected:
            kind += " · ВЗЯТО"
        lines = [html.escape(str(value)).replace("\n", "<br>") for value in values]
        self.kind.setText(kind)
        self.stats.setText("<br>".join(lines) or "Служебный узел без характеристик")
        self.adjustSize()
        screen = QApplication.screenAt(global_pos)
        geometry = screen.availableGeometry() if screen else QApplication.primaryScreen().availableGeometry()
        x = global_pos.x() + 18
        y = global_pos.y() + 18
        if x + self.width() > geometry.right():
            x = global_pos.x() - self.width() - 18
        if y + self.height() > geometry.bottom():
            y = global_pos.y() - self.height() - 18
        self.move(max(geometry.left(), x), max(geometry.top(), y))
        self.show()
        self.raise_()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor("#c0a16b"), 1))
        length = 13
        # Small double-corner ornaments echo the in-game tooltip without image assets.
        for x, sx in ((2, 1), (self.width() - 3, -1)):
            for y, sy in ((2, 1), (self.height() - 3, -1)):
                painter.drawLine(x, y, x + sx * length, y)
                painter.drawLine(x, y, x, y + sy * length)
                painter.drawLine(x + sx * 4, y + sy * 4, x + sx * 10, y + sy * 4)
                painter.drawLine(x + sx * 4, y + sy * 4, x + sx * 4, y + sy * 10)


class CleanPassiveTreeCanvas(CompleteTooltipTreeCanvas):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.node_tooltip = PoePassiveTooltip()

    def _node_size(self, node):
        # Full-tree scale is ~0.025. Icons remain tiny until the user zooms in.
        normal = clamp(4.2 + (self.scale - 0.025) * 88.0, 3.2, 17.0)
        if node.get("isKeystone"):
            return normal * 2.0
        if node.get("isNotable") or node.get("isMastery"):
            return normal * 1.48
        if node.get("classStartIndex") is not None:
            return normal * 2.2
        return normal

    def _draw_clean_node(self, painter, node_id, active):
        node = self.nodes.get(node_id, {})
        point = self.positions.get(node_id)
        if point is None:
            return
        screen = self._screen(point)
        if not self.rect().adjusted(-25, -25, 25, 25).contains(screen.toPoint()):
            return
        size = self._node_size(node)
        target = QRectF(screen.x() - size / 2, screen.y() - size / 2, size, size)
        icon_key = node.get("icon", "")
        coords = self.sprite_coords["active" if active else "inactive"].get(icon_key)
        sprite = self.active_sprite if active else self.inactive_sprite
        if coords and not sprite.isNull() and size >= 4.0:
            source = QRectF(coords["x"], coords["y"], coords["w"], coords["h"])
            clip = QPainterPath()
            clip.addEllipse(target)
            painter.save()
            painter.setClipPath(clip)
            painter.setOpacity(1.0 if active else 0.42)
            painter.drawPixmap(target, sprite, source)
            painter.restore()
        else:
            painter.setBrush(QColor("#182035") if active else QColor("#17171b"))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(target)
        if active:
            border = QColor("#88ff8d") if node_id in self.added else QColor("#28d34f")
            width = 1.6 if size > 7 else 1.0
        else:
            border = QColor(112, 91, 54, 155)
            width = 0.7
        painter.setOpacity(1.0)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(border, width))
        painter.drawEllipse(target.adjusted(-1, -1, 1, 1))

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
        painter.setPen(QPen(QColor(83, 70, 47, 105), 0.65))
        for first, second in self.edges:
            a, b = self._screen(self.positions[first]), self._screen(self.positions[second])
            if visible_rect.contains(a.toPoint()) or visible_rect.contains(b.toPoint()):
                painter.drawLine(a, b)
        painter.setPen(QPen(QColor("#1fd448"), 1.45))
        for first, second in self.edges:
            if first in self.selected and second in self.selected:
                painter.drawLine(self._screen(self.positions[first]), self._screen(self.positions[second]))
        for node_id in self.positions:
            self._draw_clean_node(painter, node_id, node_id in self.selected)

    def _node_at(self, event):
        nearest = None
        nearest_distance = 10.0
        for node_id, point in self.positions.items():
            screen = self._screen(point)
            hit_radius = max(5.0, self._node_size(self.nodes.get(node_id, {})) / 2 + 3)
            if abs(screen.x() - event.x()) > hit_radius or abs(screen.y() - event.y()) > hit_radius:
                continue
            distance = math.hypot(screen.x() - event.x(), screen.y() - event.y())
            if distance < min(nearest_distance, hit_radius):
                nearest, nearest_distance = node_id, distance
        return nearest

    def mouseMoveEvent(self, event):
        if self._drag_start is not None:
            self.node_tooltip.hide()
            return PassiveTreeCanvas.mouseMoveEvent(self, event)
        node_id = self._node_at(event)
        if node_id:
            self.node_tooltip.show_node(
                self.nodes.get(node_id, {}), node_id in self.selected, event.globalPos()
            )
        else:
            self.node_tooltip.hide()

    def mousePressEvent(self, event):
        self.node_tooltip.hide()
        super().mousePressEvent(event)

    def wheelEvent(self, event):
        self.node_tooltip.hide()
        super().wheelEvent(event)

    def leaveEvent(self, event):
        self.node_tooltip.hide()
        super().leaveEvent(event)
