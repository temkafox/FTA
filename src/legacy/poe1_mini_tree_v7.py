"""Tiny native passive-tree neighbourhood around the next target node."""

from __future__ import annotations

import math

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QColor, QPainter, QPainterPath, QPen

from poe1_manual_plan_v2 import manual_passive_plan
from poe1_mini_tree_v6 import MiniPassiveRoute as BaseMiniPassiveRoute


class MiniPassiveRoute(BaseMiniPassiveRoute):
    VIEW_W = 132
    VIEW_H = 96
    WORLD_X = 760.0
    WORLD_Y = 550.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self._planned = set()
        self._immediate = set()
        self._focus_node = None
        self._layout_positions = {}
        self.setFixedSize(self.VIEW_W, self.VIEW_H)

    def _build_tree_layout(self):
        # The neighbourhood owns a fixed viewport; do not shrink it to the
        # three chronological route nodes used by older versions.
        self.setFixedSize(self.VIEW_W, self.VIEW_H)

    def set_build_level(self, build, level):
        if not build or build.get("format") != "actpilot-manual-v1":
            self._visible_nodes = []
            self._completed = set()
            self._planned = set()
            self._immediate = set()
            self._edges = []
            self._positions = {}
            self._layout_positions = {}
            self.setVisible(False)
            self.update()
            return

        plan = manual_passive_plan(build, level)
        completed = [str(node) for node in plan.get("completed", [])]
        upcoming = [str(node) for node in plan.get("upcoming", [])]
        self._completed = set(completed)
        self._planned = {str(node) for node in plan.get("planned", [])}
        self._immediate = set(upcoming[:1])
        self._focus_node = upcoming[0] if upcoming else (completed[-1] if completed else None)
        if not self._focus_node or self._focus_node not in self._nodes:
            self._visible_nodes = []
            self.setVisible(False)
            self.update()
            return

        focus = self._world_position(self._focus_node)
        visible = []
        positions = {}
        for node_id, node in self._nodes.items():
            node_id = str(node_id)
            if node.get("ascendancyName") or node.get("isAscendancyStart"):
                continue
            point = self._world_position(node_id)
            dx = (point.x() - focus.x()) / self.WORLD_X
            dy = (point.y() - focus.y()) / self.WORLD_Y
            if dx * dx + dy * dy <= 1.0:
                visible.append(node_id)
                positions[node_id] = point

        self._visible_nodes = visible
        self._positions = positions
        visible_set = set(visible)
        edges = set()
        for first in visible:
            node = self._node(first)
            for value in node.get("out", []) + node.get("in", []):
                second = str(value)
                if second in visible_set and second != first:
                    edges.add(tuple(sorted((first, second))))
        self._edges = sorted(edges)

        usable_w = self.VIEW_W - 12.0
        usable_h = self.VIEW_H - 12.0
        scale = min(usable_w / (self.WORLD_X * 2.0), usable_h / (self.WORLD_Y * 2.0))
        self._layout_positions = {
            node_id: QPointF(
                self.VIEW_W / 2.0 + (point.x() - focus.x()) * scale,
                self.VIEW_H / 2.0 + (point.y() - focus.y()) * scale,
            )
            for node_id, point in positions.items()
        }
        self.setFixedSize(self.VIEW_W, self.VIEW_H)
        self.setVisible(True)
        self.update()

    def _screen_positions(self):
        return dict(self._layout_positions)

    def _node_size(self, node_id):
        node = self._node(node_id)
        if node.get("isKeystone"):
            base = 10.0
        elif node.get("isNotable") or node.get("isMastery"):
            base = 8.0
        elif node.get("classStartIndex") is not None:
            base = 10.0
        else:
            base = 5.5
        if node_id in self._planned:
            base += 2.5
        if node_id in self._immediate:
            base += 1.5
        return base

    def _draw_local_node(self, painter, node_id, center):
        node = self._node(node_id)
        completed = node_id in self._completed
        planned = node_id in self._planned
        immediate = node_id in self._immediate
        size = self._node_size(node_id)
        target = QRectF(center.x() - size / 2, center.y() - size / 2, size, size)
        state = "active" if completed else "inactive"
        sprite = self._active_sprite if completed else self._inactive_sprite
        coords = self._sprite_coords[state].get(node.get("icon", ""))
        if coords and not sprite.isNull():
            source = QRectF(coords["x"], coords["y"], coords["w"], coords["h"])
            clip = QPainterPath()
            clip.addEllipse(target)
            painter.save()
            painter.setClipPath(clip)
            painter.setOpacity(1.0 if completed else (0.82 if planned else 0.34))
            painter.drawPixmap(target, sprite, source)
            painter.restore()
        else:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#173a27") if completed else QColor("#1b1812"))
            painter.drawEllipse(target)

        if completed:
            border, width = QColor("#39e873"), 1.5
        elif planned:
            border, width = QColor("#e0ad39"), 1.35
        else:
            border, width = QColor(115, 91, 55, 125), 0.65
        if immediate:
            border, width = QColor("#ffd36a"), 2.0
        painter.setOpacity(1.0)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(border, width))
        painter.drawEllipse(target.adjusted(-0.8, -0.8, 0.8, 0.8))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        screen = self._screen_positions()
        self._hit_centers = screen

        for first, second in self._edges:
            if first not in screen or second not in screen:
                continue
            both_planned = first in self._planned and second in self._planned
            both_completed = first in self._completed and second in self._completed
            if both_completed:
                color, width = QColor(45, 218, 102, 215), 1.35
            elif both_planned:
                color, width = QColor(205, 157, 49, 195), 1.15
            else:
                color, width = QColor(91, 73, 48, 90), 0.55
            painter.setPen(QPen(color, width, Qt.SolidLine, Qt.RoundCap))
            painter.drawLine(screen[first], screen[second])

        # Context first, route last, so important nodes cannot be obscured.
        ordered = sorted(
            self._visible_nodes,
            key=lambda node: (node in self._planned, node in self._immediate),
        )
        for node_id in ordered:
            self._draw_local_node(painter, node_id, screen[node_id])
        painter.end()

