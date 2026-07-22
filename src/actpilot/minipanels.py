"""Живые мини-панели оверлея: линии MiniPassiveRoute (v1..v8) и MiniGemLinks (v1..v5)."""

from __future__ import annotations

import math

from PyQt5.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QCursor, QFont, QPainter, QPainterPath, QPen, QPixmap
from PyQt5.QtWidgets import QApplication, QLabel, QSizePolicy, QToolTip, QWidget

from actpilot.data_cache import game_data
from actpilot.gems.data import badges_for, gem_art_path
from actpilot.gems.widgets import (
    GRANTED_NON_GEMS, ICON_DIR, ICON_INDEX, AcquisitionGemTooltip,
)
from actpilot.tree import CachedZoomSafeTreeCanvas
from poe1_builds import stage_for_level
from poe1_level_plan_v5 import quest_aware_passive_plan
from poe1_manual_build_v4 import load_tree
from poe1_manual_plan_v2 import manual_passive_plan
from poe1_widgets import GEM_COLORS, infer_gem_color



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


MiniPassiveRouteV1 = MiniPassiveRoute


BaseMiniPassiveRoute = MiniPassiveRouteV1


class MiniPassiveRoute(BaseMiniPassiveRoute):
    def _pick_nodes(self, completed, upcoming):
        completed = [str(node) for node in completed if str(node) in self._nodes]
        upcoming = [str(node) for node in upcoming if str(node) in self._nodes]
        if not upcoming:
            return super()._pick_nodes(completed, upcoming)

        next_node = upcoming[0]
        last_completed = completed[-1] if completed else None
        parent = next(
            (node for node in reversed(completed) if self._connected(node, next_node)),
            None,
        )
        chosen = []
        for node in (last_completed, parent, next_node):
            if node and node not in chosen:
                chosen.append(node)
        if len(chosen) < 3:
            future = next(
                (node for node in upcoming[1:] if self._connected(next_node, node)),
                None,
            )
            if future and future not in chosen:
                chosen.append(future)
        return chosen[:3]


MiniPassiveRouteV2 = MiniPassiveRoute


BaseMiniPassiveRoute = MiniPassiveRouteV2


class MiniPassiveRoute(BaseMiniPassiveRoute):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(56)
        self.setMouseTracking(True)
        self._hit_centers = {}
        self._hovered_node = None
        self.setStyleSheet("""
            QToolTip {
                color: #eadfca;
                background: #080806;
                border: 1px solid #8a6937;
                padding: 4px 7px;
            }
        """)

    def _node_size(self, node_id):
        node = self._node(node_id)
        if node.get("isKeystone"):
            return 28.0
        if node.get("isNotable") or node.get("isMastery"):
            return 25.0
        if node.get("classStartIndex") is not None:
            return 27.0
        return 21.0

    def paintEvent(self, event):
        self._hit_centers = self._screen_positions()
        super().paintEvent(event)

    def mouseMoveEvent(self, event):
        nearest = None
        distance = float("inf")
        for node_id, center in self._hit_centers.items():
            current = math.hypot(event.x() - center.x(), event.y() - center.y())
            limit = self._node_size(node_id) / 2.0 + 5.0
            if current <= limit and current < distance:
                nearest, distance = node_id, current
        if nearest != self._hovered_node:
            self._hovered_node = nearest
            if nearest:
                QToolTip.showText(
                    event.globalPos(),
                    str(self._node(nearest).get("name") or "Passive Skill"),
                    self,
                )
            else:
                QToolTip.hideText()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self._hovered_node = None
        QToolTip.hideText()
        super().leaveEvent(event)


MiniPassiveRouteV3 = MiniPassiveRoute


BaseMiniPassiveRoute = MiniPassiveRouteV3


class MiniPassiveRoute(BaseMiniPassiveRoute):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(88, 38)

    def _pick_nodes(self, completed, upcoming):
        completed = [str(node) for node in completed if str(node) in self._nodes]
        upcoming = [str(node) for node in upcoming if str(node) in self._nodes]
        chosen = []
        # Left to right: the passive just allocated, the one to allocate now,
        # and the one immediately after it in the saved leveling route.
        if completed:
            chosen.append(completed[-1])
        chosen.extend(upcoming[:2])
        if len(chosen) < 3:
            for node in reversed(completed[:-1]):
                if node not in chosen:
                    chosen.insert(0, node)
                if len(chosen) == 3:
                    break
        return chosen[-3:]

    def set_build_level(self, build, level):
        super().set_build_level(build, level)
        # Only adjacent chronological items may receive a line. A route can
        # switch branches, so never draw a shortcut across the middle node.
        self._edges = [
            (self._visible_nodes[index], self._visible_nodes[index + 1])
            for index in range(len(self._visible_nodes) - 1)
            if self._connected(
                self._visible_nodes[index], self._visible_nodes[index + 1]
            )
        ]
        self.update()

    def _screen_positions(self):
        # The real tree coordinates are intentionally not used here: nearby
        # orbit nodes otherwise overlap in a short horizontal HUD strip.
        count = len(self._visible_nodes)
        if not count:
            return {}
        spacing = 28.0
        start_x = 16.0
        return {
            node_id: QPointF(start_x + index * spacing, self.height() / 2.0)
            for index, node_id in enumerate(self._visible_nodes)
        }

    def _node_size(self, node_id):
        node = self._node(node_id)
        if node.get("isKeystone"):
            return 21.0
        if node.get("isNotable") or node.get("isMastery"):
            return 18.0
        if node.get("classStartIndex") is not None:
            return 20.0
        return 15.0


MiniPassiveRouteV4 = MiniPassiveRoute


BaseMiniPassiveRoute = MiniPassiveRouteV4


class MiniPassiveRoute(BaseMiniPassiveRoute):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._layout_positions = {}

    def set_build_level(self, build, level):
        super().set_build_level(build, level)
        self._build_tree_layout()
        self.update()

    def _build_tree_layout(self):
        nodes = list(self._visible_nodes)
        if not nodes:
            self._layout_positions = {}
            self.setFixedSize(1, 1)
            return

        margin = 5.0
        scale = 0.01
        # Find one uniform scale that preserves the official tree geometry and
        # guarantees a visible gap between every pair of node frames.
        for index, first in enumerate(nodes):
            a = self._positions[first]
            for second in nodes[index + 1 :]:
                b = self._positions[second]
                distance = math.hypot(a.x() - b.x(), a.y() - b.y())
                if distance <= 0.001:
                    continue
                required = (
                    self._node_size(first) / 2.0
                    + self._node_size(second) / 2.0
                    + 7.0
                )
                scale = max(scale, required / distance)

        raw = {
            node: QPointF(
                self._positions[node].x() * scale,
                self._positions[node].y() * scale,
            )
            for node in nodes
        }
        min_x = min(
            raw[node].x() - self._node_size(node) / 2.0 for node in nodes
        )
        max_x = max(
            raw[node].x() + self._node_size(node) / 2.0 for node in nodes
        )
        min_y = min(
            raw[node].y() - self._node_size(node) / 2.0 for node in nodes
        )
        max_y = max(
            raw[node].y() + self._node_size(node) / 2.0 for node in nodes
        )
        self._layout_positions = {
            node: QPointF(
                point.x() - min_x + margin,
                point.y() - min_y + margin,
            )
            for node, point in raw.items()
        }
        self.setFixedSize(
            max(26, int(math.ceil(max_x - min_x + margin * 2))),
            max(26, int(math.ceil(max_y - min_y + margin * 2))),
        )

    def _screen_positions(self):
        return dict(self._layout_positions)


MiniPassiveRouteV5 = MiniPassiveRoute


BaseMiniPassiveRoute = MiniPassiveRouteV5


class MiniPassiveRoute(BaseMiniPassiveRoute):
    def _pick_nodes(self, completed, upcoming):
        completed = [str(node) for node in completed if str(node) in self._nodes]
        upcoming = [str(node) for node in upcoming if str(node) in self._nodes]
        chosen = []
        # Exactly: previous allocated -> most recently allocated -> next target.
        chosen.extend(completed[-2:])
        if upcoming:
            chosen.append(upcoming[0])
        elif len(completed) >= 3:
            chosen = completed[-3:]
        return chosen[-3:]


MiniPassiveRouteV6 = MiniPassiveRoute


BaseMiniPassiveRoute = MiniPassiveRouteV6


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


MiniPassiveRouteV7 = MiniPassiveRoute


BaseMiniPassiveRoute = MiniPassiveRouteV7


class MiniPassiveRoute(BaseMiniPassiveRoute):
    _graph = None

    def _tree_graph(self):
        if self.__class__._graph is None:
            graph = {str(node_id): set() for node_id in self._nodes}
            for node_id, node in self._nodes.items():
                first = str(node_id)
                for value in node.get("out", []) + node.get("in", []):
                    second = str(value)
                    if second in graph:
                        graph[first].add(second)
                        graph[second].add(first)
            self.__class__._graph = graph
        return self.__class__._graph

    def set_build_level(self, build, level):
        if not build or build.get("format") == "actpilot-manual-v1":
            return super().set_build_level(build, level)
        plan = quest_aware_passive_plan(
            build.get("trees", []), level, self._tree_graph(), False,
        )
        if not plan.get("target"):
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
        self._set_local_plan(plan)

    def _set_local_plan(self, plan):
        completed = [str(node) for node in plan.get("completed", [])]
        upcoming = [str(node) for node in plan.get("upcoming", [])]
        planned = [str(node) for node in plan.get("planned", [])]
        self._completed = set(completed)
        self._planned = set(planned)
        self._immediate = set(upcoming[:1])
        known_upcoming = [node for node in upcoming if node in self._nodes]
        known_completed = [node for node in completed if node in self._nodes]
        known_planned = [node for node in planned if node in self._nodes]
        self._focus_node = (
            known_upcoming[0] if known_upcoming
            else known_completed[-1] if known_completed
            else known_planned[0] if known_planned
            else None
        )
        if not self._focus_node:
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
        self.setVisible(True)
        self.update()


MiniPassiveRouteV8 = MiniPassiveRoute


class MiniGemLinks(QWidget):
    ICON = 22.0
    STEP_X = 29.0
    STEP_Y = 27.0
    MARGIN = 3.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setStyleSheet("""
            background: transparent;
            QToolTip {
                color: #eadfca;
                background: #080806;
                border: 1px solid #8a6937;
                padding: 4px 7px;
            }
        """)
        self._links = []
        self._items = []
        self._pixmaps = {}
        self._hovered = None
        self.setFixedSize(1, 1)

    @staticmethod
    def _clean_links(links):
        result = []
        for link in links or []:
            gems = [
                gem for gem in link.get("gems", [])
                if (gem.get("name") or "").casefold() not in GRANTED_NON_GEMS
            ]
            if gems:
                result.append(gems)
        return result

    def set_build_level(self, build, level):
        stage = stage_for_level((build or {}).get("gem_sets", []), level)
        self._links = self._clean_links(stage.get("links", [])) if stage else []
        self._items = []
        self._hovered = None
        if not self._links:
            self.setFixedSize(1, 1)
            self.setVisible(False)
            self.update()
            return
        longest = max(len(link) for link in self._links)
        width = int(self.MARGIN * 2 + self.ICON + max(0, longest - 1) * self.STEP_X)
        height = int(self.MARGIN * 2 + self.ICON + max(0, len(self._links) - 1) * self.STEP_Y)
        self.setFixedSize(max(28, width), max(28, height))
        self.setVisible(True)
        self.update()

    def _gem_pixmap(self, gem):
        name = (gem.get("name") or "").casefold()
        if name not in self._pixmaps:
            info = ICON_INDEX.get(name, {})
            self._pixmaps[name] = (
                QPixmap(str(ICON_DIR / info.get("file", ""))) if info else QPixmap()
            )
        return self._pixmaps[name]

    def _layout_items(self):
        rows = []
        items = []
        for row_index, gems in enumerate(self._links):
            y = self.MARGIN + row_index * self.STEP_Y
            row = []
            for column, gem in enumerate(gems):
                x = self.MARGIN + column * self.STEP_X
                rect = QRectF(x, y, self.ICON, self.ICON)
                row.append((gem, rect))
                items.append((gem, rect))
            rows.append(row)
        self._items = items
        return rows

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        rows = self._layout_items()
        painter.setPen(QPen(QColor(199, 151, 56, 185), 1.2, Qt.SolidLine, Qt.RoundCap))
        for row in rows:
            for (_, first), (_, second) in zip(row, row[1:]):
                painter.drawLine(
                    QPointF(first.right() + 1.0, first.center().y()),
                    QPointF(second.left() - 1.0, second.center().y()),
                )
        for row in rows:
            for gem, rect in row:
                pixmap = self._gem_pixmap(gem)
                if not pixmap.isNull():
                    painter.drawPixmap(rect, pixmap, QRectF(pixmap.rect()))
                    continue
                color_name = infer_gem_color(gem.get("name", ""))
                dark, light = GEM_COLORS.get(color_name, GEM_COLORS["white"])
                painter.setBrush(dark)
                painter.setPen(QPen(light, 1.0))
                painter.drawEllipse(rect.adjusted(2, 2, -2, -2))
        painter.end()

    def _gem_at(self, point):
        for gem, rect in self._items:
            if rect.adjusted(-2, -2, 2, 2).contains(point):
                return gem
        return None

    def mouseMoveEvent(self, event):
        gem = self._gem_at(event.pos())
        name = (gem.get("name") or "").strip() if gem else ""
        if name != self._hovered:
            self._hovered = name or None
            if name:
                QToolTip.showText(event.globalPos(), name, self)
            else:
                QToolTip.hideText()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self._hovered = None
        QToolTip.hideText()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            gem = self._gem_at(event.pos())
            name = (gem.get("name") or "").strip() if gem else ""
            if name:
                QApplication.clipboard().setText(name)
                QToolTip.showText(event.globalPos(), f"Скопировано: {name}", self)
                event.accept()
                return
        super().mousePressEvent(event)


MiniGemLinksV1 = MiniGemLinks


BaseMiniGemLinks = MiniGemLinksV1


class MiniGemLinks(BaseMiniGemLinks):
    HEADER_H = 15.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self._range_label = ""

    @staticmethod
    def _range_for(stages, active):
        stages = sorted(stages or [], key=lambda item: int(item.get("level", 1)))
        if not active or not stages:
            return ""
        index = next((i for i, stage in enumerate(stages) if stage is active), -1)
        if index < 0:
            active_level = int(active.get("level", 1))
            index = next(
                (i for i, stage in enumerate(stages) if int(stage.get("level", 1)) == active_level),
                0,
            )
        start = int(stages[index].get("level", 1))
        if index + 1 < len(stages):
            return f"{start}–{int(stages[index + 1].get('level', 1)) - 1}"
        return f"{start}+"

    def set_build_level(self, build, level):
        stages = (build or {}).get("gem_sets", [])
        active = stage_for_level(stages, level)
        self._range_label = self._range_for(stages, active)
        super().set_build_level(build, level)
        if self._links:
            self.setFixedHeight(int(self.height() + self.HEADER_H))

    def _layout_items(self):
        rows = super()._layout_items()
        shifted = []
        items = []
        for row in rows:
            shifted_row = []
            for gem, rect in row:
                moved = QRectF(rect)
                moved.translate(0, self.HEADER_H)
                shifted_row.append((gem, moved))
                items.append((gem, moved))
            shifted.append(shifted_row)
        self._items = items
        return shifted

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self._range_label:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.TextAntialiasing)
        painter.setFont(QFont("Segoe UI", 8, QFont.DemiBold))
        painter.setPen(QColor("#d7b86a"))
        painter.drawText(
            QRectF(0, 0, self.width(), self.HEADER_H),
            Qt.AlignCenter,
            self._range_label,
        )
        painter.end()


MiniGemLinksV2 = MiniGemLinks


BaseMiniGemLinks = MiniGemLinksV2


class MiniGemLinks(BaseMiniGemLinks):
    _fallback_files = None

    @classmethod
    def _fallbacks(cls):
        if cls._fallback_files is None:
            result = {}
            any_file = None
            for name, info in ICON_INDEX.items():
                filename = info.get("file", "")
                path = ICON_DIR / filename
                if not filename or not path.is_file():
                    continue
                any_file = any_file or filename
                result.setdefault(infer_gem_color(name), filename)
            result.setdefault("white", any_file)
            cls._fallback_files = result
        return cls._fallback_files

    def _gem_pixmap(self, gem):
        pixmap = super()._gem_pixmap(gem)
        if not pixmap.isNull():
            return pixmap
        name = (gem.get("name") or "").casefold()
        color = infer_gem_color(gem.get("name", ""))
        filename = self._fallbacks().get(color) or self._fallbacks().get("white")
        fallback = QPixmap(str(ICON_DIR / filename)) if filename else QPixmap()
        self._pixmaps[name] = fallback
        return fallback


MiniGemLinksV3 = MiniGemLinks


GEM_COLOURS = game_data("gem_colors.json")


GEM_LEVELS = game_data("gem_levels.json")


def gem_colour(name):
    key = (name or "").strip().casefold()
    return GEM_COLOURS.get(key) or infer_gem_color(name)


def required_level(name):
    record = GEM_LEVELS.get((name or "").strip().casefold(), {})
    requirements = record.get("requirements", {})
    try:
        return int(requirements.get("1"))
    except (TypeError, ValueError):
        return None


class MiniGemTooltip(AcquisitionGemTooltip):
    def __init__(self):
        super().__init__()
        self.requirement = QLabel()
        self.requirement.setAlignment(Qt.AlignCenter)
        self.requirement.setFont(QFont("Segoe UI", 9, QFont.DemiBold))
        self.requirement.setStyleSheet(
            "color:#e7c56d; border-top:1px solid #334038; padding-top:7px;"
        )
        layout = self.layout()
        index = layout.indexOf(self.acquisition)
        layout.insertWidget(index, self.requirement)

    def show_mini_gem(self, gem, class_name, global_pos):
        super().show_acquisition(gem, class_name, global_pos)
        name = gem.get("name", "")
        level = required_level(name)
        badges = badges_for(name, class_name)
        ways = " / ".join(badges) if badges else "—"
        level_text = str(level) if level is not None else "неизвестен"
        self.requirement.setText(
            f"Требуемый уровень: {level_text}   ·   Получение: {ways}"
        )
        self.requirement.show()
        self.adjustSize()
        self.show()
        self.raise_()


BaseMiniGemLinks = MiniGemLinksV3


class MiniGemLinks(BaseMiniGemLinks):
    _fallback_files = None
    tooltip = None

    def __init__(self, parent=None):
        super().__init__(parent)
        self.character_class = ""
        if MiniGemLinks.tooltip is None:
            MiniGemLinks.tooltip = MiniGemTooltip()

    @classmethod
    def _fallbacks(cls):
        if cls._fallback_files is None:
            result = {}
            any_file = None
            for name, info in ICON_INDEX.items():
                filename = info.get("file", "")
                if not filename or not (ICON_DIR / filename).is_file():
                    continue
                any_file = any_file or filename
                result.setdefault(gem_colour(name), filename)
            result.setdefault("white", any_file)
            cls._fallback_files = result
        return cls._fallback_files

    def set_build_level(self, build, level):
        self.character_class = (build or {}).get("class", "")
        super().set_build_level(build, level)

    def _gem_pixmap(self, gem):
        name = (gem.get("name") or "").casefold()
        info = ICON_INDEX.get(name, {})
        filename = info.get("file", "")
        if filename and (ICON_DIR / filename).is_file():
            if name not in self._pixmaps or self._pixmaps[name].isNull():
                self._pixmaps[name] = QPixmap(str(ICON_DIR / filename))
            return self._pixmaps[name]
        color = gem_colour(gem.get("name", ""))
        fallback_file = self._fallbacks().get(color) or self._fallbacks().get("white")
        cache_key = f"{name}|fallback:{color}"
        if cache_key not in self._pixmaps:
            self._pixmaps[cache_key] = (
                QPixmap(str(ICON_DIR / fallback_file)) if fallback_file else QPixmap()
            )
        return self._pixmaps[cache_key]

    def mouseMoveEvent(self, event):
        gem = self._gem_at(event.pos())
        name = (gem.get("name") or "").strip() if gem else ""
        if name != self._hovered:
            self._hovered = name or None
            if gem and name:
                self.tooltip.show_mini_gem(gem, self.character_class, QCursor.pos())
            else:
                self.tooltip.hide()
        # Skip the base name-only QToolTip; the full card replaces it.
        event.accept()

    def leaveEvent(self, event):
        self._hovered = None
        self.tooltip.hide()
        super(BaseMiniGemLinks, self).leaveEvent(event)

    def mousePressEvent(self, event):
        self.tooltip.hide()
        super().mousePressEvent(event)


MiniGemLinksV4 = MiniGemLinks


BaseMiniGemLinks = MiniGemLinksV4


class MiniGemLinks(BaseMiniGemLinks):
    def _gem_pixmap(self, gem):
        path = gem_art_path(gem)
        if not path:
            return QPixmap()
        key = f"art:{path.name}"
        if key not in self._pixmaps or self._pixmaps[key].isNull():
            self._pixmaps[key] = QPixmap(str(path))
        return self._pixmaps[key]


MiniGemLinksV5 = MiniGemLinks


# Ловушка: leaveEvent v4-класса читает BaseMiniGemLinks в рантайме — имя обязано остаться на v3-классе
BaseMiniGemLinks = MiniGemLinksV3
