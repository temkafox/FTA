"""Compact, separate renderer for the imported PoE 1 ascendancy route."""

from __future__ import annotations

import json
import math
from pathlib import Path

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QColor, QFont, QPainter, QPen
from PyQt5.QtWidgets import QLabel, QVBoxLayout, QWidget

from poe1_ascendancy_plan import ascendancy_plan
from poe1_tree_renderer_v2 import PoePassiveTooltip


TREE_FILE = Path(__file__).parent / "data" / "poe1" / "skilltree.json"


class AscendancyRouteCanvas(QWidget):
    def __init__(self, nodes, positions, parent=None):
        super().__init__(parent)
        self.setMinimumSize(280, 360)
        self.setMouseTracking(True)
        self.node_data = nodes
        self.positions = positions
        self.plan = {"nodes": [], "edges": [], "completed": [], "next": []}
        self.screen_positions = {}
        self.tooltip = PoePassiveTooltip()

    def set_plan(self, plan):
        self.plan = plan
        self.update()

    def _layout(self):
        ids = [node_id for node_id in self.plan.get("nodes", []) if node_id in self.positions]
        if not ids:
            self.screen_positions = {}
            return
        xs = [self.positions[node_id].x() for node_id in ids]
        ys = [self.positions[node_id].y() for node_id in ids]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        margin_x, margin_y = 50.0, 48.0
        width = max(1.0, max_x - min_x)
        height = max(1.0, max_y - min_y)
        scale = min((self.width() - margin_x * 2) / width, (self.height() - margin_y * 2) / height)
        scale = max(0.01, scale)
        used_w, used_h = width * scale, height * scale
        left = (self.width() - used_w) / 2
        top = (self.height() - used_h) / 2
        self.screen_positions = {
            node_id: QPointF(
                left + (self.positions[node_id].x() - min_x) * scale,
                top + (self.positions[node_id].y() - min_y) * scale,
            )
            for node_id in ids
        }

    def paintEvent(self, event):
        self._layout()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#07080a"))
        if not self.screen_positions:
            painter.setPen(QColor("#888888"))
            painter.drawText(self.rect(), Qt.AlignCenter, "Маршрут ассенданси не найден")
            return

        completed = set(self.plan.get("completed", []))
        next_nodes = set(self.plan.get("next", []))
        painter.setPen(QPen(QColor("#b78b24"), 2.0))
        for first, second in self.plan.get("edges", []):
            if first in self.screen_positions and second in self.screen_positions:
                painter.drawLine(self.screen_positions[first], self.screen_positions[second])
        painter.setPen(QPen(QColor("#28e562"), 2.5))
        for first, second in self.plan.get("edges", []):
            if first in self.screen_positions and second in self.screen_positions:
                if first in completed and second in completed:
                    painter.drawLine(self.screen_positions[first], self.screen_positions[second])

        for node_id, point in self.screen_positions.items():
            node = self.node_data.get(node_id, {})
            is_start = bool(node.get("isAscendancyStart"))
            radius = 21 if is_start else (17 if node.get("isNotable") else 12)
            if node_id in completed:
                border, fill = QColor("#39f072"), QColor("#123b24")
            else:
                border, fill = QColor("#e1ae35"), QColor("#3b2b0f")
            if node_id in next_nodes:
                border = QColor("#f4ffe8")
            painter.setPen(QPen(border, 3.0 if node_id in next_nodes else 2.0))
            painter.setBrush(fill)
            painter.drawEllipse(point, radius, radius)
            painter.setPen(QColor("#eee8d9"))
            painter.setFont(QFont("Georgia", 8, QFont.Bold))
            initial = (node.get("name") or "?")[:1].upper()
            painter.drawText(QRectF(point.x()-radius, point.y()-radius, radius*2, radius*2), Qt.AlignCenter, initial)

            if node.get("isNotable"):
                label = QRectF(point.x() - 72, point.y() + radius + 4, 144, 34)
                painter.setPen(QColor("#d8cdb8"))
                painter.setFont(QFont("Segoe UI", 8))
                painter.drawText(label, Qt.AlignHCenter | Qt.AlignTop | Qt.TextWordWrap, node.get("name", ""))

    def _node_at(self, position):
        nearest, best = None, 25.0
        for node_id, point in self.screen_positions.items():
            distance = math.hypot(point.x() - position.x(), point.y() - position.y())
            if distance < best:
                nearest, best = node_id, distance
        return nearest

    def mouseMoveEvent(self, event):
        node_id = self._node_at(event.pos())
        if node_id:
            self.tooltip.show_node(
                self.node_data.get(node_id, {}),
                node_id in set(self.plan.get("completed", [])),
                event.globalPos(),
            )
        else:
            self.tooltip.hide()

    def leaveEvent(self, event):
        self.tooltip.hide()
        super().leaveEvent(event)


class AscendancyProgressWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        try:
            tree = json.loads(TREE_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            tree = {}
        self.nodes = tree.get("nodes", {})
        groups = tree.get("groups", {})
        radii = tree.get("constants", {}).get("orbitRadii", [])
        counts = tree.get("constants", {}).get("skillsPerOrbit", [])
        self.positions = {}
        for node_id, node in self.nodes.items():
            group = groups.get(str(node.get("group")), {})
            orbit = int(node.get("orbit", 0))
            index = int(node.get("orbitIndex", 0))
            radius = radii[orbit] if orbit < len(radii) else 0
            count = counts[orbit] if orbit < len(counts) else 1
            angle = 2 * math.pi * index / max(1, count)
            self.positions[str(node_id)] = QPointF(
                float(group.get("x", 0)) + radius * math.sin(angle),
                float(group.get("y", 0)) - radius * math.cos(angle),
            )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 10, 8, 8)
        layout.setSpacing(7)
        self.header = QLabel("Ассенданси")
        self.header.setAlignment(Qt.AlignCenter)
        self.header.setWordWrap(True)
        self.header.setStyleSheet("color:#e6c477; font-weight:600;")
        layout.addWidget(self.header)
        self.canvas = AscendancyRouteCanvas(self.nodes, self.positions)
        layout.addWidget(self.canvas, 1)
        legend = QLabel("Зелёное — получено · золотое — будущий маршрут · светлая рамка — следующая лаборатория")
        legend.setWordWrap(True)
        legend.setStyleSheet("color:#777777;")
        layout.addWidget(legend)

    def set_build(self, build, level):
        if not build:
            self.header.setText("Импортируйте PoB")
            self.canvas.set_plan({"nodes": [], "edges": [], "completed": [], "next": []})
            return
        plan = ascendancy_plan(
            build.get("trees", []), self.nodes, build.get("ascendancy", ""), level
        )
        self.canvas.set_plan(plan)
        next_lab = plan.get("next_lab")
        if next_lab:
            names = [self.nodes.get(node_id, {}).get("name", "Пассив") for node_id in plan.get("next", [])]
            self.header.setText(f"{plan['name']} · далее: {next_lab}\n" + " → ".join(names))
        elif plan.get("nodes"):
            self.header.setText(f"{plan['name']} · маршрут завершён")
        else:
            self.header.setText(f"{plan['name']} · маршрут не найден")
