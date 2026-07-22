"""Живая линия tree-канваса PoE 1: от PassiveTreeCanvas до CachedZoomSafeTreeCanvas."""

from __future__ import annotations

import html
import json
import math
import re
from collections import deque
from pathlib import Path

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QPixmap
from PyQt5.QtWidgets import (
    QApplication, QFrame, QLabel, QSizePolicy, QToolTip, QVBoxLayout, QWidget,
)

from actpilot.paths import get_resource_dir
from poe1_ascendancy_plan import ascendancy_plan


ROOT = get_resource_dir() / "data" / "poe1"
TREE_FILE = ROOT / "skilltree.json"



def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


MASTERY_PAIR = re.compile(r"\{\s*(\d+)\s*,\s*(\d+)\s*\}")


def parse_mastery_selection(raw: str) -> dict[str, int]:
    return {node_id: int(effect_id) for node_id, effect_id in MASTERY_PAIR.findall(raw or "")}


class PassiveTreeCanvas(QWidget):
    def __init__(self, tree_file: Path = TREE_FILE, parent=None):
        super().__init__(parent)
        self.setMinimumSize(520, 390)
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.nodes = {}
        self.positions = {}
        self.edges = []
        self.selected = set()
        self.added = set()
        self.center = QPointF(0, 0)
        self.scale = 0.035
        self._drag_start = None
        self._load(tree_file)

    def _load(self, path: Path):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        self.nodes = data.get("nodes", {})
        groups = data.get("groups", {})
        radii = data.get("constants", {}).get("orbitRadii", [])
        counts = data.get("constants", {}).get("skillsPerOrbit", [])
        for node_id, node in self.nodes.items():
            group = groups.get(str(node.get("group")), {})
            orbit = int(node.get("orbit", 0))
            index = int(node.get("orbitIndex", 0))
            radius = radii[orbit] if orbit < len(radii) else 0
            count = counts[orbit] if orbit < len(counts) else 1
            angle = 2 * math.pi * index / max(1, count)
            x = float(group.get("x", 0)) + radius * math.sin(angle)
            y = float(group.get("y", 0)) - radius * math.cos(angle)
            self.positions[str(node_id)] = QPointF(x, y)
        seen = set()
        for node_id, node in self.nodes.items():
            for other in node.get("out", []):
                edge = tuple(sorted((str(node_id), str(other))))
                if edge not in seen and edge[0] in self.positions and edge[1] in self.positions:
                    seen.add(edge)
                    self.edges.append(edge)

    def set_stage(self, nodes: list[int], previous_nodes: list[int] | None = None):
        self.selected = {str(node) for node in nodes if str(node) in self.positions}
        previous = {str(node) for node in (previous_nodes or [])}
        self.added = self.selected - previous
        self.fit_selected()
        self.update()

    def fit_selected(self):
        points = [self.positions[node] for node in self.selected if node in self.positions]
        if not points:
            return self.fit_all()
        min_x, max_x = min(p.x() for p in points), max(p.x() for p in points)
        min_y, max_y = min(p.y() for p in points), max(p.y() for p in points)
        self.center = QPointF((min_x + max_x) / 2, (min_y + max_y) / 2)
        width, height = max(1200, max_x - min_x), max(1200, max_y - min_y)
        self.scale = min(max(0.018, (self.width() - 80) / width), max(0.018, (self.height() - 80) / height), 0.22)

    def fit_all(self):
        if not self.positions:
            return
        xs = [p.x() for p in self.positions.values()]
        ys = [p.y() for p in self.positions.values()]
        self.center = QPointF((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)
        self.scale = min((self.width() - 30) / (max(xs) - min(xs)), (self.height() - 30) / (max(ys) - min(ys)))
        self.update()

    def _screen(self, point: QPointF) -> QPointF:
        return QPointF(
            (point.x() - self.center.x()) * self.scale + self.width() / 2,
            (point.y() - self.center.y()) * self.scale + self.height() / 2,
        )

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#111116"))
        if not self.positions:
            painter.setPen(QColor("#aaaaaa"))
            painter.drawText(self.rect(), Qt.AlignCenter, "Данные дерева PoE 1 не найдены")
            return
        painter.setPen(QPen(QColor(75, 75, 84, 120), 1))
        for first, second in self.edges:
            a, b = self._screen(self.positions[first]), self._screen(self.positions[second])
            if self.rect().adjusted(-20, -20, 20, 20).contains(a.toPoint()) or self.rect().contains(b.toPoint()):
                painter.drawLine(a, b)
        painter.setPen(QPen(QColor("#9d7735"), 2))
        for first, second in self.edges:
            if first in self.selected and second in self.selected:
                painter.drawLine(self._screen(self.positions[first]), self._screen(self.positions[second]))
        radius = max(1.3, min(3.2, 1.5 + self.scale * 8))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(82, 82, 92, 180))
        for node_id, point in self.positions.items():
            screen = self._screen(point)
            if self.rect().contains(screen.toPoint()):
                painter.drawEllipse(screen, radius, radius)
        for node_id in self.selected:
            screen = self._screen(self.positions[node_id])
            painter.setPen(QPen(QColor("#f3d18a"), 1.5))
            painter.setBrush(QColor("#9d6827"))
            painter.drawEllipse(screen, 5.5, 5.5)
        for node_id in self.added:
            screen = self._screen(self.positions[node_id])
            painter.setPen(QPen(QColor("#d7ffcf"), 1.5))
            painter.setBrush(QColor("#42c95e"))
            painter.drawEllipse(screen, 6.5, 6.5)

    def wheelEvent(self, event):
        old_scale = self.scale
        factor = 1.18 if event.angleDelta().y() > 0 else 1 / 1.18
        self.scale = max(0.008, min(0.65, self.scale * factor))
        cursor = event.pos()
        world_x = self.center.x() + (cursor.x() - self.width() / 2) / old_scale
        world_y = self.center.y() + (cursor.y() - self.height() / 2) / old_scale
        self.center = QPointF(
            world_x - (cursor.x() - self.width() / 2) / self.scale,
            world_y - (cursor.y() - self.height() / 2) / self.scale,
        )
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start = event.pos()
            self.setCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        if self._drag_start is not None:
            delta = event.pos() - self._drag_start
            self._drag_start = event.pos()
            self.center -= QPointF(delta.x() / self.scale, delta.y() / self.scale)
            self.update()
            return
        nearest = None
        nearest_distance = 11.0
        for node_id in self.selected:
            point = self._screen(self.positions[node_id])
            distance = math.hypot(point.x() - event.x(), point.y() - event.y())
            if distance < nearest_distance:
                nearest, nearest_distance = node_id, distance
        if nearest:
            node = self.nodes.get(nearest, {})
            QToolTip.showText(event.globalPos(), node.get("name", f"Узел {nearest}"), self)

    def mouseReleaseEvent(self, event):
        self._drag_start = None
        self.unsetCursor()

    def mouseDoubleClickEvent(self, event):
        self.fit_selected()
        self.update()


class DetailedPassiveTreeCanvas(PassiveTreeCanvas):
    ZOOM_KEY = "0.2972"

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.active_sprite = QPixmap(str(ROOT / "skills-2.jpg"))
        self.inactive_sprite = QPixmap(str(ROOT / "skills-disabled-2.jpg"))
        self.sprite_coords = {"active": {}, "inactive": {}}
        self._prepare_tree()

    def _prepare_tree(self):
        try:
            data = json.loads((ROOT / "skilltree.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        ascendancy_ids = {
            str(node_id) for node_id, node in self.nodes.items()
            if node.get("ascendancyName") or node.get("isAscendancyStart")
        }
        for node_id in ascendancy_ids:
            self.positions.pop(node_id, None)
        self.edges = [
            edge for edge in self.edges
            if edge[0] in self.positions and edge[1] in self.positions
        ]
        sprite_groups = (
            ("normalActive", "active"), ("notableActive", "active"),
            ("keystoneActive", "active"), ("normalInactive", "inactive"),
            ("notableInactive", "inactive"), ("keystoneInactive", "inactive"),
        )
        for source_key, target_key in sprite_groups:
            group = data.get("sprites", {}).get(source_key, {}).get(self.ZOOM_KEY, {})
            self.sprite_coords[target_key].update(group.get("coords", {}))

    def set_stage(self, nodes: list[int], previous_nodes: list[int] | None = None):
        filtered = [node for node in nodes if str(node) in self.positions]
        previous = [node for node in (previous_nodes or []) if str(node) in self.positions]
        super().set_stage(filtered, previous)

    def _draw_node_icon(self, painter, node_id, active):
        node = self.nodes.get(node_id, {})
        point = self.positions.get(node_id)
        if point is None:
            return
        screen = self._screen(point)
        if not self.rect().adjusted(-30, -30, 30, 30).contains(screen.toPoint()):
            return
        icon_key = node.get("icon", "")
        coords = self.sprite_coords["active" if active else "inactive"].get(icon_key)
        sprite = self.active_sprite if active else self.inactive_sprite
        if coords and not sprite.isNull():
            source = QRectF(coords["x"], coords["y"], coords["w"], coords["h"])
            base_size = 12 if not node.get("isNotable") else 18
            if node.get("isKeystone"):
                base_size = 23
            size = max(base_size, min(base_size * 1.7, base_size * (0.9 + self.scale * 5)))
            target = QRectF(screen.x() - size / 2, screen.y() - size / 2, size, size)
            painter.drawPixmap(target, sprite, source)
        else:
            painter.setPen(QPen(QColor("#777"), 1))
            painter.setBrush(QColor("#24242a"))
            painter.drawEllipse(screen, 3.0, 3.0)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.fillRect(self.rect(), QColor("#08090b"))
        if not self.positions:
            painter.setPen(QColor("#aaa"))
            painter.drawText(self.rect(), Qt.AlignCenter, "Данные дерева не найдены")
            return
        painter.setPen(QPen(QColor(83, 70, 47, 130), 1))
        for first, second in self.edges:
            a, b = self._screen(self.positions[first]), self._screen(self.positions[second])
            if self.rect().adjusted(-20, -20, 20, 20).contains(a.toPoint()) or self.rect().contains(b.toPoint()):
                painter.drawLine(a, b)
        painter.setPen(QPen(QColor("#39d353"), 2.4))
        for first, second in self.edges:
            if first in self.selected and second in self.selected:
                painter.drawLine(self._screen(self.positions[first]), self._screen(self.positions[second]))
        for node_id in self.positions:
            self._draw_node_icon(painter, node_id, node_id in self.selected)
        for node_id in self.selected:
            screen = self._screen(self.positions[node_id])
            color = QColor("#9aff9a") if node_id in self.added else QColor("#39d353")
            radius = 10 if self.nodes.get(node_id, {}).get("isNotable") else 7
            if self.nodes.get(node_id, {}).get("isKeystone"):
                radius = 13
            painter.setPen(QPen(color, 2))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(screen, radius, radius)

    def mouseMoveEvent(self, event):
        if self._drag_start is not None:
            return super().mouseMoveEvent(event)
        nearest = None
        nearest_distance = 13.0
        for node_id, point in self.positions.items():
            screen = self._screen(point)
            if abs(screen.x() - event.x()) > nearest_distance or abs(screen.y() - event.y()) > nearest_distance:
                continue
            distance = math.hypot(screen.x() - event.x(), screen.y() - event.y())
            if distance < nearest_distance:
                nearest, nearest_distance = node_id, distance
        if not nearest:
            QToolTip.hideText()
            return
        node = self.nodes.get(nearest, {})
        name = html.escape(node.get("name") or f"Пассив {nearest}")
        stats = node.get("stats") or []
        stat_html = "<br>".join(html.escape(str(stat)).replace("\n", "<br>") for stat in stats)
        kind = "Ключевое умение" if node.get("isKeystone") else (
            "Значимое умение" if node.get("isNotable") else "Пассивное умение"
        )
        selected = "<br><span style='color:#55d96b'>Взято в этом этапе</span>" if nearest in self.selected else ""
        QToolTip.showText(
            event.globalPos(),
            f"<div style='min-width:270px'><b style='color:#e6c477'>{name}</b><br>"
            f"<span style='color:#999'>{kind}</span><p>{stat_html or 'Нет числового описания'}</p>{selected}</div>",
            self,
        )


class CompleteTooltipTreeCanvas(DetailedPassiveTreeCanvas):
    def mouseMoveEvent(self, event):
        if self._drag_start is not None:
            return super().mouseMoveEvent(event)
        nearest = None
        nearest_distance = 13.0
        for node_id, point in self.positions.items():
            screen = self._screen(point)
            if abs(screen.x() - event.x()) > nearest_distance or abs(screen.y() - event.y()) > nearest_distance:
                continue
            distance = math.hypot(screen.x() - event.x(), screen.y() - event.y())
            if distance < nearest_distance:
                nearest, nearest_distance = node_id, distance
        if not nearest:
            QToolTip.hideText()
            return
        node = self.nodes.get(nearest, {})
        name = html.escape(node.get("name") or f"Пассив {nearest}")
        stats = list(node.get("stats") or [])
        mastery = node.get("masteryEffects") or []
        if mastery:
            stats = [
                "Вариант: " + " / ".join(str(value) for value in effect.get("stats", []))
                for effect in mastery
            ]
        stat_html = "<br>".join(
            html.escape(str(stat)).replace("\n", "<br>") for stat in stats
        )
        if node.get("isMastery"):
            kind = "Мастерство — выберите один эффект"
        elif node.get("isKeystone"):
            kind = "Ключевое умение"
        elif node.get("isNotable"):
            kind = "Значимое умение"
        else:
            kind = "Пассивное умение"
        selected = "<br><span style='color:#55d96b'>Взято в этом этапе</span>" if nearest in self.selected else ""
        QToolTip.showText(
            event.globalPos(),
            f"<div style='min-width:300px'><b style='color:#e6c477'>{name}</b><br>"
            f"<span style='color:#999'>{kind}</span><p>{stat_html or 'Служебный узел без характеристик'}</p>"
            f"{selected}</div>",
            self,
        )


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


CleanPassiveTreeCanvasV2 = CleanPassiveTreeCanvas


class ConnectedPassiveTreeCanvas(CleanPassiveTreeCanvas):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._rebuild_complete_edges()

    def _rebuild_complete_edges(self):
        edges = set()
        for node_id, node in self.nodes.items():
            first = str(node_id)
            if first not in self.positions:
                continue
            for other in node.get("out", []) + node.get("in", []):
                second = str(other)
                if second not in self.positions or second == first:
                    continue
                edges.add(tuple(sorted((first, second))))
        self.edges = sorted(edges)


class OpaqueMasteryTooltip(PoePassiveTooltip):
    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor("#050505"))
        self.setPalette(palette)
        self.setWindowOpacity(1.0)

    def show_mastery(self, node, selected, effect_id, global_pos):
        self.title.setText(node.get("name") or "Mastery")
        chosen = next(
            (effect for effect in node.get("masteryEffects", []) if int(effect.get("effect", -1)) == effect_id),
            None,
        )
        if chosen:
            self.kind.setText("МАСТЕРСТВО ВЗЯТО · ЭФФЕКТ ИЗ БИЛДА")
            values = chosen.get("stats", [])
            color = "#8ca5ff"
        elif selected:
            self.kind.setText("МАСТЕРСТВО ВЗЯТО · ЭФФЕКТ НЕ УДАЛОСЬ СОПОСТАВИТЬ")
            values = []
            color = "#d6a35f"
        else:
            self.kind.setText("МАСТЕРСТВО НЕ ВЗЯТО")
            values = []
            color = "#888888"
        lines = [html.escape(str(value)).replace("\n", "<br>") for value in values]
        self.stats.setStyleSheet(f"color:{color};")
        self.stats.setText("<br>".join(lines) or "В сохранённом билде нет выбранного эффекта")
        self._place(global_pos)

    def show_regular(self, node, selected, global_pos):
        self.stats.setStyleSheet("color:#8ca5ff;")
        super().show_node(node, selected, global_pos)

    def _place(self, global_pos):
        self.adjustSize()
        screen = QApplication.screenAt(global_pos)
        geometry = screen.availableGeometry() if screen else QApplication.primaryScreen().availableGeometry()
        x, y = global_pos.x() + 18, global_pos.y() + 18
        if x + self.width() > geometry.right():
            x = global_pos.x() - self.width() - 18
        if y + self.height() > geometry.bottom():
            y = global_pos.y() - self.height() - 18
        self.move(max(geometry.left(), x), max(geometry.top(), y))
        self.show()
        self.raise_()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#050505"))
        painter.setPen(QPen(QColor("#80643c"), 2))
        painter.drawRect(self.rect().adjusted(1, 1, -2, -2))
        painter.setPen(QPen(QColor("#c0a16b"), 1))
        length = 13
        for x, sx in ((3, 1), (self.width() - 4, -1)):
            for y, sy in ((3, 1), (self.height() - 4, -1)):
                painter.drawLine(x, y, x + sx * length, y)
                painter.drawLine(x, y, x, y + sy * length)
                painter.drawLine(x + sx * 4, y + sy * 4, x + sx * 10, y + sy * 4)
                painter.drawLine(x + sx * 4, y + sy * 4, x + sx * 4, y + sy * 10)


class MasteryAwareTreeCanvas(ConnectedPassiveTreeCanvas):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.node_tooltip.hide()
        self.node_tooltip.deleteLater()
        self.node_tooltip = OpaqueMasteryTooltip()
        self.selected_masteries = {}

    def set_masteries(self, raw: str):
        self.selected_masteries = parse_mastery_selection(raw)

    def mouseMoveEvent(self, event):
        if self._drag_start is not None:
            self.node_tooltip.hide()
            return PassiveTreeCanvas.mouseMoveEvent(self, event)
        node_id = self._node_at(event)
        if not node_id:
            self.node_tooltip.hide()
            return
        node = self.nodes.get(node_id, {})
        if node.get("isMastery"):
            self.node_tooltip.show_mastery(
                node,
                node_id in self.selected,
                self.selected_masteries.get(node_id),
                event.globalPos(),
            )
        else:
            self.node_tooltip.show_regular(node, node_id in self.selected, event.globalPos())


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


class LevelingRouteTreeCanvas(OrbitalPassiveTreeCanvas):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.completed_nodes = set()
        self.route_nodes = set()
        self.next_nodes = set()

    def set_stage(self, nodes, previous_nodes=None):
        super().set_stage(nodes, previous_nodes)
        target = set(self.selected)
        previous = {str(node) for node in (previous_nodes or []) if str(node) in target}
        if not previous:
            previous = {
                node_id for node_id in target
                if self.nodes.get(node_id, {}).get("classStartIndex") is not None
            }
        self.completed_nodes = previous
        self.route_nodes = target - previous
        adjacency = {node_id: set() for node_id in target}
        for first, second in self.edges:
            if first in target and second in target:
                adjacency[first].add(second)
                adjacency[second].add(first)
        self.next_nodes = {
            node_id for node_id in self.route_nodes
            if adjacency.get(node_id, set()) & self.completed_nodes
        }
        if not self.next_nodes and self.route_nodes:
            self.next_nodes = {next(iter(self.route_nodes))}
        self.update()

    def _draw_route_node(self, painter, node_id):
        node = self.nodes.get(node_id, {})
        point = self.positions.get(node_id)
        if point is None:
            return
        screen = self._screen(point)
        if not self.rect().adjusted(-25, -25, 25, 25).contains(screen.toPoint()):
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
            painter.setOpacity(1.0 if active else 0.42)
            painter.drawPixmap(target_rect, sprite, source)
            painter.restore()
        else:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#182035") if active else QColor("#17171b"))
            painter.drawEllipse(target_rect)

        if node_id in self.next_nodes:
            border, width, padding = QColor("#efffc1"), 2.4, 2.5
        elif node_id in self.route_nodes:
            border, width, padding = QColor("#27d94e"), 1.35, 1.0
        elif node_id in self.completed_nodes:
            border, width, padding = QColor("#e5c16f"), 1.55, 1.0
        else:
            border, width, padding = QColor(112, 91, 54, 155), 0.7, 1.0
        painter.setOpacity(1.0)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(border, width))
        painter.drawEllipse(target_rect.adjusted(-padding, -padding, padding, padding))
        if node_id in self.next_nodes:
            painter.setPen(QPen(QColor("#2af05a"), 1.2))
            painter.drawEllipse(target_rect.adjusted(-5, -5, 5, 5))

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
        painter.setPen(QPen(QColor("#d8bd72"), 1.65))
        for first, second in self.edges:
            if first in self.completed_nodes and second in self.completed_nodes:
                painter.drawPath(self._edge_path(first, second))
        painter.setPen(QPen(QColor("#22db4d"), 1.75))
        for first, second in self.edges:
            if (
                first in self.selected and second in self.selected
                and (first in self.route_nodes or second in self.route_nodes)
            ):
                painter.drawPath(self._edge_path(first, second))
        for node_id in self.positions:
            self._draw_route_node(painter, node_id)


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


class ProgressionTreeCanvas(FocusedLevelingTreeCanvas):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.upcoming_order = []
        self.preview_nodes = set()

    def set_progression(self, planned, completed, upcoming):
        super().set_stage(planned, completed)
        route = set(self.route_nodes)
        self.upcoming_order = [str(node) for node in upcoming if str(node) in route]
        self.preview_nodes = set(self.upcoming_order[:5])
        self.next_nodes = set(self.upcoming_order[:1])
        self.update()

    def upcoming_nodes(self, limit=10):
        focus = set(self.upcoming_order[:limit])
        if not focus:
            focus = set(self.completed_nodes)
        return focus

    def _draw_route_node(self, painter, node_id):
        node = self.nodes.get(node_id, {})
        point = self.positions.get(node_id)
        if point is None:
            return
        screen = self._screen(point)
        if not self.rect().adjusted(-25, -25, 25, 25).contains(screen.toPoint()):
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
            painter.setOpacity(1.0 if node_id in self.completed_nodes or node_id in self.preview_nodes else 0.58)
            painter.drawPixmap(target_rect, sprite, source)
            painter.restore()
        else:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#182035") if active else QColor("#17171b"))
            painter.drawEllipse(target_rect)

        if node_id in self.next_nodes:
            border, width, padding = QColor("#f5ffe0"), 2.6, 3.0
        elif node_id in self.preview_nodes:
            border, width, padding = QColor("#37e867"), 1.8, 1.6
        elif node_id in self.route_nodes:
            border, width, padding = QColor("#176f38"), 1.0, 1.0
        elif node_id in self.completed_nodes:
            border, width, padding = QColor("#e5c16f"), 1.55, 1.0
        else:
            border, width, padding = QColor(112, 91, 54, 155), 0.7, 1.0
        painter.setOpacity(1.0)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(border, width))
        painter.drawEllipse(target_rect.adjusted(-padding, -padding, padding, padding))

        if node_id in self.preview_nodes:
            number = self.upcoming_order.index(node_id) + 1
            badge_size = 13
            badge = QRectF(
                target_rect.right() - 3,
                target_rect.top() - 7,
                badge_size,
                badge_size,
            )
            painter.setPen(QPen(QColor("#0b160d"), 1))
            painter.setBrush(QColor("#e8ffd9") if number == 1 else QColor("#38df65"))
            painter.drawEllipse(badge)
            painter.setPen(QColor("#071108"))
            painter.setFont(QFont("Segoe UI", 7, QFont.Bold))
            painter.drawText(badge, Qt.AlignCenter, str(number))

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

        painter.setPen(QPen(QColor("#d8bd72"), 1.65))
        for first, second in self.edges:
            if first in self.completed_nodes and second in self.completed_nodes:
                painter.drawPath(self._edge_path(first, second))

        painter.setPen(QPen(QColor("#155a2d"), 1.05))
        for first, second in self.edges:
            if first in self.selected and second in self.selected and (
                first in self.route_nodes or second in self.route_nodes
            ):
                painter.drawPath(self._edge_path(first, second))

        highlighted = self.completed_nodes | self.preview_nodes
        painter.setPen(QPen(QColor("#31e761"), 2.15))
        for first, second in self.edges:
            if first in highlighted and second in highlighted and (
                first in self.preview_nodes or second in self.preview_nodes
            ):
                painter.drawPath(self._edge_path(first, second))

        for node_id in self.positions:
            self._draw_route_node(painter, node_id)


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


class ImmediateFocusTreeCanvas(LevelMappedTreeCanvas):
    def immediate_focus_nodes(self):
        if not self.upcoming_order:
            return set(self.completed_nodes)
        next_node = self.upcoming_order[0]
        focus = {next_node}
        for first, second in self.edges:
            if first == next_node and second in self.completed_nodes:
                focus.add(second)
            elif second == next_node and first in self.completed_nodes:
                focus.add(first)
        return focus

    def upcoming_nodes(self, limit=10):
        return self.immediate_focus_nodes()

    def fit_upcoming(self):
        focus = self.immediate_focus_nodes()
        points = [self.positions[node] for node in focus if node in self.positions]
        if not points:
            return self.fit_selected()
        min_x, max_x = min(point.x() for point in points), max(point.x() for point in points)
        min_y, max_y = min(point.y() for point in points), max(point.y() for point in points)
        self.center = QPointF((min_x + max_x) / 2, (min_y + max_y) / 2)
        width = max(650, max_x - min_x)
        height = max(650, max_y - min_y)
        self.scale = max(
            0.09,
            min(0.24, (self.width() - 90) / width, (self.height() - 90) / height),
        )
        self.update()


class QuestAwareTreeCanvas(ImmediateFocusTreeCanvas):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.node_markers = {}

    def set_quest_progression(self, planned, completed, upcoming, node_levels, node_markers):
        super().set_level_progression(planned, completed, upcoming, node_levels)
        self.node_markers = {str(node): str(value) for node, value in node_markers.items()}
        # Suppress the numeric badge from the parent; this renderer draws the
        # more explicit level/quest/bandit marker below.
        self.node_levels = {}
        self.update()

    def _draw_route_node(self, painter, node_id):
        super()._draw_route_node(painter, node_id)
        marker = self.node_markers.get(node_id)
        point = self.positions.get(node_id)
        if node_id not in self.route_nodes or marker is None or point is None:
            return
        screen = self._screen(point)
        size = self._node_size(self.nodes.get(node_id, {}))
        target = QRectF(screen.x() - size / 2, screen.y() - size / 2, size, size)
        width = max(16, 7 * len(marker) + 7)
        badge = QRectF(target.right() - 3, target.top() - 8, width, 15)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor("#2a1b02"), 1))
        painter.setBrush(QColor("#ffe291"))
        painter.drawRoundedRect(badge, 6, 6)
        painter.setPen(QColor("#171003"))
        painter.setFont(QFont("Segoe UI", 7, QFont.Bold))
        painter.drawText(badge, Qt.AlignCenter, marker)


class CleanPassiveTreeCanvas(QuestAwareTreeCanvas):
    def _draw_route_node(self, painter, node_id):
        # Skip QuestAwareTreeCanvas' marker overlay. Its parent still renders
        # the correct green/gold state and immediate-focus ring.
        ImmediateFocusTreeCanvas._draw_route_node(self, painter, node_id)


CleanPassiveTreeCanvasV11 = CleanPassiveTreeCanvas


class NativeAscendancyTreeCanvas(CleanPassiveTreeCanvas):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ascendancy = {"name": "Ассенданси", "nodes": [], "edges": [], "completed": [], "next": []}

    def set_ascendancy_build(self, build, level):
        if not build:
            self.ascendancy = {"name": "Ассенданси", "nodes": [], "edges": [], "completed": [], "next": []}
        else:
            plan = ascendancy_plan(
                build.get("trees", []), self.nodes,
                build.get("ascendancy", ""), level,
            )
            route = list(plan.get("nodes", []))
            completed = list(plan.get("completed", []))
            if route and route[0] not in completed:
                completed.insert(0, route[0])
            plan["completed"] = completed
            self.ascendancy = plan
        self.update()

    def fit_ascendancy(self):
        points = [
            self.positions[node_id] for node_id in self.ascendancy.get("nodes", [])
            if node_id in self.positions
        ]
        if not points:
            return
        min_x, max_x = min(point.x() for point in points), max(point.x() for point in points)
        min_y, max_y = min(point.y() for point in points), max(point.y() for point in points)
        self.center = QPointF((min_x + max_x) / 2, (min_y + max_y) / 2)
        width, height = max(1050.0, max_x - min_x), max(900.0, max_y - min_y)
        self.scale = min(
            max(0.04, (self.width() - 90) / width),
            max(0.04, (self.height() - 90) / height),
            0.38,
        )
        self.update()

    def _draw_ascendancy_node(self, painter, node_id):
        point = self.positions.get(node_id)
        if point is None:
            return
        screen = self._screen(point)
        if not self.rect().adjusted(-30, -30, 30, 30).contains(screen.toPoint()):
            return
        node = self.nodes.get(node_id, {})
        size = max(8.0, self._node_size(node))
        if node.get("isAscendancyStart"):
            size *= 1.55
        target = QRectF(screen.x() - size / 2, screen.y() - size / 2, size, size)
        completed = node_id in set(self.ascendancy.get("completed", []))
        next_node = node_id in set(self.ascendancy.get("next", []))
        icon_key = node.get("icon", "")
        coords = self.sprite_coords["active" if completed else "inactive"].get(icon_key)
        sprite = self.active_sprite if completed else self.inactive_sprite
        if coords and not sprite.isNull():
            source = QRectF(coords["x"], coords["y"], coords["w"], coords["h"])
            clip = QPainterPath()
            clip.addEllipse(target)
            painter.save()
            painter.setClipPath(clip)
            painter.setOpacity(1.0 if completed else 0.78)
            painter.drawPixmap(target, sprite, source)
            painter.restore()
        else:
            painter.setBrush(QColor("#123b24") if completed else QColor("#3b2b0f"))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(target)
        border = QColor("#39f072") if completed else QColor("#e1ae35")
        if next_node:
            border = QColor("#f4ffe8")
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(border, 2.7 if next_node else 1.8))
        painter.drawEllipse(target.adjusted(-2, -2, 2, 2))

    def _paint_native_ascendancy(self, painter):
        route = set(self.ascendancy.get("nodes", []))
        if not route:
            return
        completed = set(self.ascendancy.get("completed", []))
        painter.setPen(QPen(QColor("#d3a326"), 2.0))
        for first, second in self.ascendancy.get("edges", []):
            if first in self.positions and second in self.positions:
                painter.drawLine(self._screen(self.positions[first]), self._screen(self.positions[second]))
        painter.setPen(QPen(QColor("#28e562"), 2.5))
        for first, second in self.ascendancy.get("edges", []):
            if first in completed and second in completed:
                painter.drawLine(self._screen(self.positions[first]), self._screen(self.positions[second]))
        for node_id in route:
            self._draw_ascendancy_node(painter, node_id)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        self._paint_native_ascendancy(painter)

    def _asc_node_at(self, event):
        nearest, limit = None, 13.0
        route = set(self.ascendancy.get("nodes", []))
        for node_id in route:
            point = self.positions.get(node_id)
            if point is None:
                continue
            screen = self._screen(point)
            radius = max(7.0, self._node_size(self.nodes.get(node_id, {})) / 2 + 4)
            distance = math.hypot(screen.x() - event.x(), screen.y() - event.y())
            if distance < min(limit, radius):
                nearest, limit = node_id, distance
        return nearest

    def mouseMoveEvent(self, event):
        node_id = self._asc_node_at(event)
        if node_id:
            self.node_tooltip.show_node(
                self.nodes.get(node_id, {}),
                node_id in set(self.ascendancy.get("completed", [])),
                event.globalPos(),
            )
            return
        super().mouseMoveEvent(event)


class RestoredAscendancyTreeCanvas(NativeAscendancyTreeCanvas):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._restore_ascendancy_positions()

    def _restore_ascendancy_positions(self):
        try:
            data = json.loads(TREE_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        groups = data.get("groups", {})
        constants = data.get("constants", {})
        radii = constants.get("orbitRadii", [])
        counts = constants.get("skillsPerOrbit", [])
        for node_id, node in data.get("nodes", {}).items():
            if not node.get("ascendancyName"):
                continue
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


# Импорт после определения OpaqueMasteryTooltip: poe1_tooltips_ru тянет его обратно из этого модуля
from poe1_tooltips_ru import RussianPassiveTooltip


class RussianDescriptionTreeCanvas(RestoredAscendancyTreeCanvas):
    def __init__(self, parent=None):
        super().__init__(parent)
        for node_id, node in self.nodes.items():
            node["_id"] = str(node_id)
        self.node_tooltip.hide()
        self.node_tooltip.deleteLater()
        self.node_tooltip = RussianPassiveTooltip()


from poe1_tooltips_ru_v3 import OfficialRussianPassiveTooltip


class OfficialRussianTreeCanvas(RussianDescriptionTreeCanvas):
    def __init__(self, parent=None):
        super().__init__(parent)
        old = self.node_tooltip
        self.node_tooltip = OfficialRussianPassiveTooltip()
        old.deleteLater()


class SeparateMasteryTreeCanvas(OfficialRussianTreeCanvas):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.mastery_ids = {
            node_id for node_id, node in self.nodes.items() if node.get("isMastery")
        }
        # Mastery is a choice unlocked by a cluster, not a travel node. Do not
        # draw even a dim structural spoke from it into the ordinary route.
        self.edges = [
            (first, second) for first, second in self.edges
            if first not in self.mastery_ids and second not in self.mastery_ids
        ]
        self.completed_masteries = set()
        self.next_mastery = None

    def set_mastery_progression(self, completed, next_node=None):
        self.completed_masteries = {str(node) for node in completed}
        self.next_mastery = str(next_node) if next_node is not None else None
        self.update()

    def _draw_route_node(self, painter, node_id):
        super()._draw_route_node(painter, node_id)
        if node_id not in self.mastery_ids:
            return
        point = self.positions.get(node_id)
        if point is None:
            return
        screen = self._screen(point)
        size = self._node_size(self.nodes.get(node_id, {}))
        rect = QRectF(screen.x() - size / 2, screen.y() - size / 2, size, size)
        if node_id in self.completed_masteries:
            color, width, padding = QColor("#32e567"), 2.2, 2.0
        elif node_id == self.next_mastery:
            color, width, padding = QColor("#fff0ad"), 2.8, 3.5
        else:
            return
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(color, width))
        painter.drawEllipse(rect.adjusted(-padding, -padding, padding, padding))


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


class ZoomScaledNodeMixin:
    def _node_size(self, node):
        # Screen-space icons must become genuinely small on an overview.
        # The previous 3.2 px floor turned notables/keystones into overlapping
        # 8-12 px circles while their tree positions were only a few px apart.
        normal = max(1.35, min(15.0, self.scale * 70.0))
        if node.get("isKeystone"):
            return normal * 1.82
        if node.get("isNotable") or node.get("isMastery"):
            return normal * 1.38
        if node.get("classStartIndex") is not None or node.get("isAscendancyStart"):
            return normal * 1.9
        return normal


class ZoomSafeTreeCanvas(ZoomScaledNodeMixin, ExplicitProgressionTreeCanvas):
    pass


class CachedZoomSafeTreeCanvas(ZoomSafeTreeCanvas):
    """Final renderer initialised directly instead of through 15 ancestors."""

    _tree_data = None
    _active_sprite = None
    _inactive_sprite = None

    @classmethod
    def _shared_data(cls):
        if cls._tree_data is None:
            cls._tree_data = json.loads(TREE_FILE.read_text(encoding="utf-8"))
        return cls._tree_data

    @classmethod
    def _shared_sprites(cls):
        if cls._active_sprite is None:
            cls._active_sprite = QPixmap(str(ROOT / "skills-2.jpg"))
            cls._inactive_sprite = QPixmap(str(ROOT / "skills-disabled-2.jpg"))
        return cls._active_sprite, cls._inactive_sprite

    def __init__(self, parent=None):
        # Deliberately call QWidget directly. The inherited constructor chain
        # parses the same 6.5 MB payload three times and rebuilds edges twice.
        QWidget.__init__(self, parent)
        self.setMinimumSize(520, 390)
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        data = self._shared_data()
        self.nodes = data.get("nodes", {})
        self.positions = {}
        self.edges = []
        self.selected = set()
        self.added = set()
        self.center = QPointF(0, 0)
        self.scale = 0.035
        self._drag_start = None

        groups = data.get("groups", {})
        constants = data.get("constants", {})
        radii = constants.get("orbitRadii", [])
        counts = constants.get("skillsPerOrbit", [])
        self.group_centers = {
            str(group_id): QPointF(float(group.get("x", 0)), float(group.get("y", 0)))
            for group_id, group in groups.items()
        }
        self.orbit_radii = radii
        self.orbit_counts = counts

        ascendancy_ids = set()
        for node_id, node in self.nodes.items():
            key = str(node_id)
            node["_id"] = key
            group = groups.get(str(node.get("group")), {})
            orbit = int(node.get("orbit", 0))
            index = int(node.get("orbitIndex", 0))
            radius = radii[orbit] if orbit < len(radii) else 0
            count = counts[orbit] if orbit < len(counts) else 1
            angle = 2 * math.pi * index / max(1, count)
            self.positions[key] = QPointF(
                float(group.get("x", 0)) + radius * math.sin(angle),
                float(group.get("y", 0)) - radius * math.cos(angle),
            )
            if node.get("ascendancyName") or node.get("isAscendancyStart"):
                ascendancy_ids.add(key)

        # Reconstruct complete ordinary-tree edges once. Ascendancy and
        # mastery connections are rendered by their dedicated layers.
        edges = set()
        for node_id, node in self.nodes.items():
            first = str(node_id)
            if first in ascendancy_ids or node.get("isMastery"):
                continue
            for other in node.get("out", []) + node.get("in", []):
                second = str(other)
                other_node = self.nodes.get(second, {})
                if (
                    second == first
                    or second not in self.positions
                    or second in ascendancy_ids
                    or other_node.get("isMastery")
                ):
                    continue
                edges.add(tuple(sorted((first, second))))
        self.edges = sorted(edges)

        self.active_sprite, self.inactive_sprite = self._shared_sprites()
        self.sprite_coords = {"active": {}, "inactive": {}}
        zoom_key = "0.2972"
        for source_key, target_key in (
            ("normalActive", "active"), ("notableActive", "active"),
            ("keystoneActive", "active"), ("normalInactive", "inactive"),
            ("notableInactive", "inactive"), ("keystoneInactive", "inactive"),
        ):
            group = data.get("sprites", {}).get(source_key, {}).get(zoom_key, {})
            self.sprite_coords[target_key].update(group.get("coords", {}))

        self.selected_masteries = {}
        self.node_tooltip = OfficialRussianPassiveTooltip()
        self.node_levels = {}
        self.node_markers = {}
        self.upcoming_order = []
        self.preview_nodes = set()
        self.completed_nodes = set()
        self.route_nodes = set()
        self.next_nodes = set()
        self.mastery_ids = {
            node_id for node_id, node in self.nodes.items() if node.get("isMastery")
        }
        self.completed_masteries = set()
        self.next_mastery = None
        self.progression_edges = set()
        self.ascendancy = {
            "name": "Ассенданси", "nodes": [], "edges": [], "completed": [], "next": [],
        }
        self._asc_screen = {}
        self._asc_panel = QRectF()
