"""Render one explicit leveling route instead of every edge between selected nodes."""

from __future__ import annotations

import math

from PyQt5.QtCore import QPointF, Qt
from PyQt5.QtGui import QColor, QPainter, QPen

from poe1_tree_renderer_v18 import SeparateMasteryTreeCanvas


class ExplicitProgressionTreeCanvas(SeparateMasteryTreeCanvas):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.progression_edges = set()

    def _distance(self, first, second):
        a, b = self.positions.get(first), self.positions.get(second)
        if a is None or b is None:
            return float("inf")
        return math.hypot(a.x() - b.x(), a.y() - b.y())

    def _explicit_edges(self, ordered_nodes):
        order = [str(node) for node in ordered_nodes if str(node) in self.positions]
        wanted = set(order)
        rank = {node: index for index, node in enumerate(order)}
        adjacency = {node: set() for node in wanted}
        for first, second in self.edges:
            if first in wanted and second in wanted:
                adjacency[first].add(second)
                adjacency[second].add(first)

        starts = [
            node for node in order
            if self.nodes.get(node, {}).get("classStartIndex") is not None
        ]
        allocated = set(starts[:1] or order[:1])
        remaining = wanted - allocated
        result = set()
        while remaining:
            frontier = []
            for node in remaining:
                parents = adjacency.get(node, set()) & allocated
                for parent in parents:
                    frontier.append((rank[node], self._distance(node, parent), node, parent))
            if not frontier:
                # A genuinely disconnected component stays visually disconnected;
                # no invented line is drawn between unrelated passive nodes.
                allocated.add(min(remaining, key=lambda node: rank[node]))
                remaining -= allocated
                continue
            _, _, node, parent = min(frontier)
            result.add(tuple(sorted((node, parent))))
            allocated.add(node)
            remaining.remove(node)
        return result

    def set_quest_progression(self, planned, completed, upcoming, node_levels, node_markers):
        super().set_quest_progression(
            planned, completed, upcoming, node_levels, node_markers,
        )
        self.progression_edges = self._explicit_edges(planned)
        self.update()

    def fit_upcoming(self):
        if self.next_mastery and self.next_mastery in self.positions:
            self.center = QPointF(self.positions[self.next_mastery])
            self.scale = 0.20
            self.update()
            return
        super().fit_upcoming()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.fillRect(self.rect(), QColor("#07080a"))
        if not self.positions:
            painter.setPen(QColor("#aaa"))
            painter.drawText(self.rect(), Qt.AlignCenter, "Данные дерева не найдены")
            painter.end()
            return

        visible_rect = self.rect().adjusted(-20, -20, 20, 20)
        painter.setPen(QPen(QColor(83, 70, 47, 95), 0.65))
        for first, second in self.edges:
            a, b = self._screen(self.positions[first]), self._screen(self.positions[second])
            if visible_rect.contains(a.toPoint()) or visible_rect.contains(b.toPoint()):
                painter.drawPath(self._edge_path(first, second))

        painter.setPen(QPen(QColor("#25ce58"), 1.9))
        for first, second in self.progression_edges:
            if first in self.completed_nodes and second in self.completed_nodes:
                painter.drawPath(self._edge_path(first, second))

        painter.setPen(QPen(QColor("#c89b36"), 1.8))
        for first, second in self.progression_edges:
            if first in self.selected and second in self.selected and (
                first in self.next_nodes or second in self.next_nodes
            ):
                painter.drawPath(self._edge_path(first, second))

        for node_id in self.positions:
            self._draw_route_node(painter, node_id)
        self._paint_native_ascendancy(painter)
        painter.end()
