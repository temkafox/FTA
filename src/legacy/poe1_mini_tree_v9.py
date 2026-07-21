"""Bright rectangular native-tree crop with every nearby passive visible."""

from __future__ import annotations

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QColor, QPainter, QPainterPath, QPen

from poe1_mini_tree_v8 import MiniPassiveRoute as BaseMiniPassiveRoute


class MiniPassiveRoute(BaseMiniPassiveRoute):
    def set_build_level(self, build, level):
        super().set_build_level(build, level)
        if self._focus_node and self._focus_node in self._nodes:
            self._fill_rectangular_crop()

    def _fill_rectangular_crop(self):
        focus = self._world_position(self._focus_node)
        visible = []
        positions = {}
        # Match a true rectangular crop of the official tree. The previous
        # ellipse silently omitted valid passives in all four corners.
        for node_id, node in self._nodes.items():
            node_id = str(node_id)
            if node.get("ascendancyName") or node.get("isAscendancyStart"):
                continue
            point = self._world_position(node_id)
            if (
                abs(point.x() - focus.x()) <= self.WORLD_X
                and abs(point.y() - focus.y()) <= self.WORLD_Y
            ):
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
        scale = min(
            usable_w / (self.WORLD_X * 2.0),
            usable_h / (self.WORLD_Y * 2.0),
        )
        self._layout_positions = {
            node_id: QPointF(
                self.VIEW_W / 2.0 + (point.x() - focus.x()) * scale,
                self.VIEW_H / 2.0 + (point.y() - focus.y()) * scale,
            )
            for node_id, point in positions.items()
        }
        self.setFixedSize(self.VIEW_W, self.VIEW_H)
        self.setVisible(bool(visible))
        self.update()

    def _node_size(self, node_id):
        node = self._node(node_id)
        if node.get("isKeystone"):
            base = 10.5
        elif node.get("isNotable") or node.get("isMastery"):
            base = 8.0
        elif node.get("classStartIndex") is not None:
            base = 10.0
        else:
            base = 5.5
        if node_id in self._planned:
            base += 2.0
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
            # Keep every passive readable. State is communicated by the
            # official active/inactive art plus route frames and lines.
            painter.setOpacity(1.0 if completed else (0.94 if planned else 0.76))
            painter.drawPixmap(target, sprite, source)
            painter.restore()
        else:
            painter.setPen(Qt.NoPen)
            if node.get("isMastery"):
                painter.setBrush(QColor(43, 38, 29, 225))
            elif completed:
                painter.setBrush(QColor(35, 92, 55, 235))
            else:
                painter.setBrush(QColor(53, 47, 37, 225))
            painter.drawEllipse(target)

        if completed:
            border, width = QColor("#39e873"), 1.45
        elif planned:
            border, width = QColor("#e0ad39"), 1.35
        else:
            border, width = QColor(138, 110, 67, 210), 0.8
        if immediate:
            border, width = QColor("#ffd36a"), 2.0
        painter.setOpacity(1.0)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(border, width))
        painter.drawEllipse(target.adjusted(-0.8, -0.8, 0.8, 0.8))

