"""Tiny, label-free passive route preview for the main PoE 1 overlay."""

from __future__ import annotations

import math

from PyQt5.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QPainter, QPainterPath, QPen
from PyQt5.QtWidgets import QSizePolicy, QWidget

from poe1_manual_build_v4 import load_tree
from poe1_manual_plan_v2 import manual_passive_plan
from poe1_tree_fast import CachedZoomSafeTreeCanvas


class MiniPassiveRoute(QWidget):
    """Draw only the last allocated node and the next one or two route nodes."""

    activated = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(68)
        self.setMinimumWidth(150)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self._data = load_tree()
        self._nodes = self._data.get("nodes", {})
        self._visible_nodes = []
        self._completed = set()
        self._edges = []
        self._positions = {}
        self._active_sprite, self._inactive_sprite = CachedZoomSafeTreeCanvas._shared_sprites()
        self._sprite_coords = {"active": {}, "inactive": {}}
        zoom_key = "0.2972"
        sprites = self._data.get("sprites", {})
        for source_key, target_key in (
            ("normalActive", "active"),
            ("notableActive", "active"),
            ("keystoneActive", "active"),
            ("normalInactive", "inactive"),
            ("notableInactive", "inactive"),
            ("keystoneInactive", "inactive"),
        ):
            group = sprites.get(source_key, {}).get(zoom_key, {})
            self._sprite_coords[target_key].update(group.get("coords", {}))

    def _node(self, node_id):
        return self._nodes.get(str(node_id), {})

    def _connected(self, first, second):
        if not first or not second:
            return False
        first, second = str(first), str(second)
        node = self._node(first)
        neighbours = {str(value) for value in node.get("out", []) + node.get("in", [])}
        if second in neighbours:
            return True
        other = self._node(second)
        return first in {str(value) for value in other.get("out", []) + other.get("in", [])}

    def _world_position(self, node_id):
        node = self._node(node_id)
        group = self._data.get("groups", {}).get(str(node.get("group")), {})
        constants = self._data.get("constants", {})
        radii = constants.get("orbitRadii", [])
        counts = constants.get("skillsPerOrbit", [])
        orbit = int(node.get("orbit", 0))
        index = int(node.get("orbitIndex", 0))
        radius = radii[orbit] if orbit < len(radii) else 0
        count = counts[orbit] if orbit < len(counts) else 1
        angle = 2 * math.pi * index / max(1, count)
        return QPointF(
            float(group.get("x", 0)) + radius * math.sin(angle),
            float(group.get("y", 0)) - radius * math.cos(angle),
        )

    def _pick_nodes(self, completed, upcoming):
        completed = [str(node) for node in completed if str(node) in self._nodes]
        upcoming = [str(node) for node in upcoming if str(node) in self._nodes]
        if upcoming:
            next_node = upcoming[0]
            parent = next(
                (node for node in reversed(completed) if self._connected(node, next_node)),
                completed[-1] if completed else None,
            )
            future = next(
                (node for node in upcoming[1:] if self._connected(next_node, node)),
                None,
            )
            return [node for node in (parent, next_node, future) if node]

        if not completed:
            return []
        last = completed[-1]
        parent = next(
            (node for node in reversed(completed[:-1]) if self._connected(node, last)),
            None,
        )
        grandparent = next(
            (
                node for node in reversed(completed[:-1])
                if parent and node != last and self._connected(node, parent)
            ),
            None,
        )
        return [node for node in (grandparent, parent, last) if node]

    def set_build_level(self, build, level):
        if not build or build.get("format") != "actpilot-manual-v1":
            self._visible_nodes = []
            self._completed = set()
            self._edges = []
            self.setVisible(False)
            self.update()
            return
        plan = manual_passive_plan(build, level)
        self._completed = {str(node) for node in plan.get("completed", [])}
        self._visible_nodes = self._pick_nodes(
            plan.get("completed", []), plan.get("upcoming", [])
        )
        self._edges = [
            (first, second)
            for index, first in enumerate(self._visible_nodes)
            for second in self._visible_nodes[index + 1 :]
            if self._connected(first, second)
        ]
        self._positions = {
            node_id: self._world_position(node_id) for node_id in self._visible_nodes
        }
        self.setVisible(bool(self._visible_nodes))
        self.update()

    def _screen_positions(self):
        if not self._positions:
            return {}
        points = list(self._positions.values())
        min_x = min(point.x() for point in points)
        max_x = max(point.x() for point in points)
        min_y = min(point.y() for point in points)
        max_y = max(point.y() for point in points)
        span_x = max(1.0, max_x - min_x)
        span_y = max(1.0, max_y - min_y)
        usable_w = max(44.0, self.width() - 62.0)
        usable_h = max(34.0, self.height() - 18.0)
        scale = min(usable_w / span_x, usable_h / span_y)
        center_x = (min_x + max_x) / 2.0
        center_y = (min_y + max_y) / 2.0
        return {
            node_id: QPointF(
                self.width() / 2.0 + (point.x() - center_x) * scale,
                self.height() / 2.0 + (point.y() - center_y) * scale,
            )
            for node_id, point in self._positions.items()
        }

    def _node_size(self, node_id):
        node = self._node(node_id)
        if node.get("isKeystone"):
            return 39.0
        if node.get("isNotable") or node.get("isMastery"):
            return 34.0
        if node.get("classStartIndex") is not None:
            return 38.0
        return 29.0

    def _draw_node(self, painter, node_id, center):
        completed = node_id in self._completed
        node = self._node(node_id)
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
            painter.setOpacity(1.0 if completed else 0.86)
            painter.drawPixmap(target, sprite, source)
            painter.restore()
        else:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#173a27") if completed else QColor("#33270f"))
            painter.drawEllipse(target)
        painter.setOpacity(1.0)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor("#39e873") if completed else QColor("#d5a638"), 2.2))
        painter.drawEllipse(target.adjusted(-1.5, -1.5, 1.5, 1.5))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        screen = self._screen_positions()
        for first, second in self._edges:
            both_completed = first in self._completed and second in self._completed
            painter.setPen(QPen(
                QColor("#34db69") if both_completed else QColor("#c99a31"),
                2.2,
                Qt.SolidLine,
                Qt.RoundCap,
            ))
            painter.drawLine(screen[first], screen[second])
        for node_id in self._visible_nodes:
            self._draw_node(painter, node_id, screen[node_id])
        painter.end()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.rect().contains(event.pos()):
            self.activated.emit()
            event.accept()
            return
        super().mouseReleaseEvent(event)

