"""Passive tree renderer with official-style orbital arcs."""

from __future__ import annotations

import json
import math

from PyQt5.QtCore import QPointF, Qt
from PyQt5.QtGui import QColor, QPainter, QPainterPath, QPen

from poe1_tree_renderer_v4 import MasteryAwareTreeCanvas
from poe1_widgets import TREE_FILE


class OrbitalPassiveTreeCanvas(MasteryAwareTreeCanvas):
    def __init__(self, parent=None):
        super().__init__(parent)
        try:
            data = json.loads(TREE_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        self.group_centers = {
            str(group_id): QPointF(float(group.get("x", 0)), float(group.get("y", 0)))
            for group_id, group in data.get("groups", {}).items()
        }
        constants = data.get("constants", {})
        self.orbit_radii = constants.get("orbitRadii", [])
        self.orbit_counts = constants.get("skillsPerOrbit", [])

    def _edge_path(self, first, second):
        first_node = self.nodes.get(first, {})
        second_node = self.nodes.get(second, {})
        first_group = str(first_node.get("group"))
        second_group = str(second_node.get("group"))
        first_orbit = int(first_node.get("orbit", 0))
        second_orbit = int(second_node.get("orbit", 0))
        path = QPainterPath()
        path.moveTo(self._screen(self.positions[first]))
        if (
            first_group == second_group
            and first_orbit == second_orbit
            and first_orbit > 0
            and first_orbit < len(self.orbit_radii)
            and first_orbit < len(self.orbit_counts)
            and first_group in self.group_centers
        ):
            count = max(1, self.orbit_counts[first_orbit])
            start = 2 * math.pi * int(first_node.get("orbitIndex", 0)) / count
            end = 2 * math.pi * int(second_node.get("orbitIndex", 0)) / count
            delta = (end - start + math.pi) % (2 * math.pi) - math.pi
            radius = self.orbit_radii[first_orbit]
            center = self.group_centers[first_group]
            segments = max(4, min(24, int(abs(delta) * 12)))
            for index in range(1, segments + 1):
                angle = start + delta * index / segments
                world = QPointF(
                    center.x() + radius * math.sin(angle),
                    center.y() - radius * math.cos(angle),
                )
                path.lineTo(self._screen(world))
        else:
            path.lineTo(self._screen(self.positions[second]))
        return path

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
                painter.drawPath(self._edge_path(first, second))
        painter.setPen(QPen(QColor("#1fd448"), 1.45))
        for first, second in self.edges:
            if first in self.selected and second in self.selected:
                painter.drawPath(self._edge_path(first, second))
        for node_id in self.positions:
            self._draw_clean_node(painter, node_id, node_id in self.selected)
