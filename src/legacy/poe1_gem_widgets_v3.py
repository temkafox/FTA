"""Compact gem chains rendered with real in-game inventory artwork."""

from __future__ import annotations

from pathlib import Path

from PyQt5.QtCore import QRectF, Qt
from PyQt5.QtGui import QFont, QPainter, QPixmap
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QWidget

from actpilot.data_cache import game_data
from poe1_combined_widgets import CompactGemChains, CompactGemIcon


ROOT = Path(__file__).parent / "data" / "poe1"
ICON_DIR = ROOT / "gem_icons"
ICON_INDEX = game_data("gem_icons.json")


class ArtworkGemIcon(CompactGemIcon):
    def __init__(self, gem, parent=None):
        super().__init__(gem, parent)
        info = ICON_INDEX.get((gem.get("name") or "").casefold(), {})
        self.art = QPixmap(str(ICON_DIR / info.get("file", ""))) if info else QPixmap()

    def paintEvent(self, event):
        if self.art.isNull():
            return super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        target = QRectF(1, 1, self.width() - 2, self.height() - 2)
        painter.drawPixmap(target, self.art, QRectF(self.art.rect()))


class ArtworkGemChains(CompactGemChains):
    def set_links(self, title, links):
        while self.layout.count():
            item = self.layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        heading = QLabel(title)
        heading.setAlignment(Qt.AlignCenter)
        heading.setFont(QFont("Segoe UI", 11, QFont.DemiBold))
        heading.setStyleSheet(
            "color:#dadada; padding-bottom:8px; border-bottom:2px solid #258de5;"
        )
        self.layout.addWidget(heading)
        for link in links:
            row_widget = QWidget()
            row_widget.setStyleSheet("background:transparent;")
            row = QHBoxLayout(row_widget)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(1)
            infinity = QLabel("∞")
            infinity.setFixedWidth(35)
            infinity.setAlignment(Qt.AlignCenter)
            infinity.setFont(QFont("Georgia", 25, QFont.Bold))
            infinity.setStyleSheet("color:#e0a34b;")
            row.addWidget(infinity)
            for index, gem in enumerate(link.get("gems", [])):
                if index:
                    connector = QLabel("—")
                    connector.setFixedWidth(14)
                    connector.setAlignment(Qt.AlignCenter)
                    connector.setStyleSheet("color:#d89c44; font-size:17px;")
                    row.addWidget(connector)
                row.addWidget(ArtworkGemIcon(gem))
            row.addStretch()
            self.layout.addWidget(row_widget)
        self.layout.addStretch()
