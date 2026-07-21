"""Compact gem chains, rich gem tooltips and focused leveling tree."""

from __future__ import annotations

import html
from collections import deque

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QColor, QCursor, QFont, QPainter, QPainterPath, QPen, QRadialGradient
from PyQt5.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget,
)

from poe1_target_widgets import GEM_CATALOG
from poe1_tree_renderer_v6 import LevelingRouteTreeCanvas
from poe1_widgets import GEM_COLORS, infer_gem_color


class GemDetailTooltip(QFrame):
    def __init__(self):
        super().__init__(None, Qt.ToolTip | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setAutoFillBackground(True)
        self.setWindowOpacity(1.0)
        self.setFixedWidth(470)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 13)
        layout.setSpacing(7)
        self.title = QLabel()
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setFont(QFont("Georgia", 14, QFont.DemiBold))
        self.title.setStyleSheet("color:#29d8c7; border-bottom:1px solid #497261; padding-bottom:7px;")
        layout.addWidget(self.title)
        self.meta = QLabel()
        self.meta.setAlignment(Qt.AlignCenter)
        self.meta.setFont(QFont("Georgia", 9))
        self.meta.setStyleSheet("color:#aaa69d;")
        layout.addWidget(self.meta)
        self.description = QLabel()
        self.description.setTextFormat(Qt.RichText)
        self.description.setWordWrap(True)
        self.description.setAlignment(Qt.AlignCenter)
        self.description.setFont(QFont("Georgia", 10))
        self.description.setStyleSheet("color:#28d8d0;")
        layout.addWidget(self.description)
        self.details = QLabel()
        self.details.setTextFormat(Qt.RichText)
        self.details.setWordWrap(True)
        self.details.setAlignment(Qt.AlignCenter)
        self.details.setFont(QFont("Georgia", 10))
        self.details.setStyleSheet("color:#9b9cff;")
        layout.addWidget(self.details)

    def show_gem(self, gem, global_pos):
        info = GEM_CATALOG.get((gem.get("name") or "").casefold(), {})
        name = gem.get("name") or "Камень"
        self.title.setText(name.upper())
        kind = "КАМЕНЬ ПОДДЕРЖКИ" if gem.get("support") else "АКТИВНЫЙ КАМЕНЬ"
        level = gem.get("level") or "—"
        quality = gem.get("quality") or "0"
        self.meta.setText(f"{kind} · УРОВЕНЬ {level} · КАЧЕСТВО +{quality}%")
        description = info.get("description") or "Описание отсутствует в данных Path of Building."
        self.description.setText(html.escape(description).replace("\n", "<br>"))
        color_name = info.get("color") or infer_gem_color(name)
        color_label = {"red": "СИЛА · КРАСНЫЙ", "green": "ЛОВКОСТЬ · ЗЕЛЁНЫЙ", "blue": "ИНТЕЛЛЕКТ · СИНИЙ", "white": "БЕЛЫЙ"}.get(color_name, color_name.upper())
        self.details.setText(color_label)
        self.adjustSize()
        screen = QApplication.screenAt(global_pos)
        geometry = screen.availableGeometry() if screen else QApplication.primaryScreen().availableGeometry()
        x, y = global_pos.x() + 16, global_pos.y() + 16
        if x + self.width() > geometry.right():
            x = global_pos.x() - self.width() - 16
        if y + self.height() > geometry.bottom():
            y = global_pos.y() - self.height() - 16
        self.move(max(geometry.left(), x), max(geometry.top(), y))
        self.show()
        self.raise_()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#040606"))
        painter.setPen(QPen(QColor("#476e5f"), 2))
        painter.drawRect(self.rect().adjusted(1, 1, -2, -2))
        painter.setPen(QPen(QColor("#85b6a1"), 1))
        for x, sx in ((3, 1), (self.width() - 4, -1)):
            for y, sy in ((3, 1), (self.height() - 4, -1)):
                painter.drawLine(x, y, x + sx * 14, y)
                painter.drawLine(x, y, x, y + sy * 14)


class CompactGemIcon(QWidget):
    tooltip = None

    def __init__(self, gem, parent=None):
        super().__init__(parent)
        self.gem = gem
        info = GEM_CATALOG.get((gem.get("name") or "").casefold(), {})
        self.color_name = info.get("color") or infer_gem_color(gem.get("name", ""))
        self.setFixedSize(43, 43)
        self.setCursor(Qt.PointingHandCursor)
        if CompactGemIcon.tooltip is None:
            CompactGemIcon.tooltip = GemDetailTooltip()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        dark, light = GEM_COLORS.get(self.color_name, GEM_COLORS["white"])
        center = QPointF(21.5, 21.5)
        painter.setPen(QPen(QColor("#a98542"), 2))
        painter.setBrush(QColor("#10151b"))
        painter.drawEllipse(center, 19, 19)
        gradient = QRadialGradient(center - QPointF(5, 6), 22)
        gradient.setColorAt(0, light)
        gradient.setColorAt(0.45, dark)
        gradient.setColorAt(1, QColor("#071018"))
        crystal = QPainterPath()
        if self.gem.get("support"):
            crystal.addRoundedRect(QRectF(9, 9, 25, 25), 7, 7)
        else:
            crystal.moveTo(21.5, 6)
            crystal.lineTo(36, 21.5)
            crystal.lineTo(21.5, 37)
            crystal.lineTo(7, 21.5)
            crystal.closeSubpath()
        painter.setBrush(gradient)
        painter.setPen(QPen(light, 1.2))
        painter.drawPath(crystal)
        painter.setPen(QColor("white"))
        painter.setFont(QFont("Segoe UI", 10, QFont.Bold))
        painter.drawText(self.rect(), Qt.AlignCenter, (self.gem.get("name") or "?")[:1].upper())

    def enterEvent(self, event):
        self.tooltip.show_gem(self.gem, QCursor.pos())
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.tooltip.hide()
        super().leaveEvent(event)


class CompactGemChains(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.body = QWidget()
        self.body.setStyleSheet("background:#08090b;")
        self.layout = QVBoxLayout(self.body)
        self.layout.setContentsMargins(14, 14, 10, 14)
        self.layout.setSpacing(14)
        self.setWidget(self.body)

    def set_links(self, title, links):
        while self.layout.count():
            item = self.layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        heading = QLabel(title)
        heading.setAlignment(Qt.AlignCenter)
        heading.setFont(QFont("Segoe UI", 11, QFont.DemiBold))
        heading.setStyleSheet("color:#dadada; padding-bottom:8px; border-bottom:2px solid #258de5;")
        self.layout.addWidget(heading)
        for link in links:
            row_widget = QWidget()
            row_widget.setStyleSheet("background:transparent;")
            row = QHBoxLayout(row_widget)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(1)
            infinity = QLabel("∞")
            infinity.setFixedWidth(35)
            infinity.setAlignment(Qt.AlignCenter)
            infinity.setFont(QFont("Georgia", 25, QFont.Bold))
            infinity.setStyleSheet("color:#e0a34b;")
            row.addWidget(infinity)
            for index, gem in enumerate(link.get("gems", [])):
                if index:
                    connector = QLabel("—")
                    connector.setFixedWidth(14)
                    connector.setAlignment(Qt.AlignCenter)
                    connector.setStyleSheet("color:#d89c44; font-size:17px;")
                    row.addWidget(connector)
                row.addWidget(CompactGemIcon(gem))
            row.addStretch()
            self.layout.addWidget(row_widget)
        self.layout.addStretch()


class FocusedLevelingTreeCanvas(LevelingRouteTreeCanvas):
    def upcoming_nodes(self, limit=10):
        adjacency = {node_id: set() for node_id in self.selected}
        for first, second in self.edges:
            if first in adjacency and second in adjacency:
                adjacency[first].add(second)
                adjacency[second].add(first)
        queue = deque(self.next_nodes)
        result = set(self.next_nodes)
        while queue and len(result) < limit:
            node = queue.popleft()
            for other in adjacency.get(node, set()):
                if other in self.route_nodes and other not in result:
                    result.add(other)
                    queue.append(other)
                    if len(result) >= limit:
                        break
        for node in list(self.next_nodes):
            result.update(adjacency.get(node, set()) & self.completed_nodes)
        return result

    def fit_upcoming(self):
        focus = self.upcoming_nodes()
        points = [self.positions[node] for node in focus if node in self.positions]
        if not points:
            return self.fit_selected()
        min_x, max_x = min(point.x() for point in points), max(point.x() for point in points)
        min_y, max_y = min(point.y() for point in points), max(point.y() for point in points)
        self.center = QPointF((min_x + max_x) / 2, (min_y + max_y) / 2)
        width, height = max(900, max_x - min_x), max(900, max_y - min_y)
        self.scale = max(0.055, min(0.22, (self.width() - 100) / width, (self.height() - 100) / height))
        self.update()
