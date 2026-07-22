"""Гем-виджеты с описаниями; DetailedPassiveTreeCanvas переехал в actpilot.tree."""

from __future__ import annotations

import html
import re
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from actpilot.data_cache import game_data
from actpilot.tree import DetailedPassiveTreeCanvas
from poe1_builds import clamp_level, stage_for_level
from poe1_widgets import GemCard, GemIcon, GemLinksView


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
