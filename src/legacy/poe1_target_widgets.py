"""Target-quality PoE 1 tree and gem link widgets."""

from __future__ import annotations

import html
import json
import math
import re
from pathlib import Path

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel, QToolTip, QVBoxLayout

from actpilot.data_cache import game_data
from poe1_builds import clamp_level, stage_for_level
from poe1_widgets import GemCard, GemIcon, GemLinksView, PassiveTreeCanvas


ROOT = Path(__file__).parent / "data" / "poe1"
CATALOG_FILE = ROOT / "gem_catalog.json"
GEM_CATALOG = game_data("gem_catalog.json")

RANGE_PATTERN = re.compile(r"(?<!\d)(\d{1,3})\s*[-–—]\s*(\d{1,3})(?!\d)")


def leveling_stage(stages: list[dict], level: int) -> dict | None:
    """Prefer an explicitly named level range, then use the normal PoB fallback."""
    level = clamp_level(level)
    for stage in stages:
        match = RANGE_PATTERN.search(stage.get("title", ""))
        if match and int(match.group(1)) <= level <= int(match.group(2)):
            return stage
    return stage_for_level(stages, level)


def gem_info(name: str) -> dict:
    return GEM_CATALOG.get((name or "").casefold(), {})


class DescribedGemIcon(GemIcon):
    def __init__(self, gem: dict, parent=None):
        enriched = dict(gem)
        info = gem_info(gem.get("name", ""))
        if info.get("color"):
            enriched["color"] = info["color"]
        super().__init__(enriched, parent)
        title = html.escape(gem.get("name", "Камень"))
        kind = "Камень поддержки" if gem.get("support") else "Активный камень"
        description = html.escape(info.get("description", "Описание отсутствует"))
        description = description.replace("\n", "<br>")
        details = []
        if gem.get("level"):
            details.append(f"Уровень камня: {html.escape(str(gem['level']))}")
        if gem.get("quality"):
            details.append(f"Качество: {html.escape(str(gem['quality']))}%")
        self.setToolTip(
            f"<div style='min-width:260px'><b style='color:#e6c477'>{title}</b><br>"
            f"<span style='color:#aaa'>{kind}</span><p>{description}</p>"
            + ("<br>".join(details) if details else "") + "</div>"
        )


class DescribedGemCard(GemCard):
    def __init__(self, gem: dict, parent=None):
        QFrame.__init__(self, parent)
        self.setFixedWidth(150)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(3)
        layout.addWidget(DescribedGemIcon(gem), 0, Qt.AlignHCenter)
        name = QLabel(gem.get("name", "Камень"))
        name.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        name.setWordWrap(True)
        name.setFixedHeight(38)
        name.setStyleSheet("color:#eeeeee;")
        layout.addWidget(name)


class DescribedGemLinksView(GemLinksView):
    def set_links(self, title: str, links: list[dict]):
        while self.layout.count():
            item = self.layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        heading = QLabel(title)
        heading.setFont(QFont("Segoe UI", 13, QFont.DemiBold))
        heading.setStyleSheet("color:white;")
        self.layout.addWidget(heading)
        if not links:
            self.layout.addWidget(QLabel("На этом этапе связки не найдены."))
        for link in links:
            block = QFrame()
            block.setStyleSheet(
                "QFrame{background:#151518;border:1px solid #34343d;border-radius:9px;}"
            )
            vertical = QVBoxLayout(block)
            label = QLabel(link.get("label", "Связка"))
            label.setFont(QFont("Segoe UI", 11, QFont.DemiBold))
            label.setStyleSheet("color:#e6c477;border:none;background:transparent;")
            vertical.addWidget(label)
            row = QHBoxLayout()
            row.setSpacing(0)
            for index, gem in enumerate(link.get("gems", [])):
                if index:
                    connector = QLabel("∞")
                    connector.setFixedWidth(25)
                    connector.setAlignment(Qt.AlignCenter)
                    connector.setStyleSheet(
                        "color:#e0a84c;border:none;background:transparent;font-size:24px;"
                    )
                    row.addWidget(connector)
                row.addWidget(DescribedGemCard(gem))
            row.addStretch()
            vertical.addLayout(row)
            self.layout.addWidget(block)
        self.layout.addStretch()


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
