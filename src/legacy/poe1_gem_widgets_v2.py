"""Compact gem links with a visible current gem-level badge."""

from PyQt5.QtCore import QRectF, Qt
from PyQt5.QtGui import QColor, QFont, QPainter, QPen
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QWidget

from poe1_combined_widgets import CompactGemChains, CompactGemIcon


class LevelGemIcon(CompactGemIcon):
    def paintEvent(self, event):
        super().paintEvent(event)
        level = self.gem.get("level")
        if level in (None, ""):
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        badge = QRectF(27, 27, 15, 15)
        painter.setPen(QPen(QColor("#d7b864"), 1))
        painter.setBrush(QColor("#050709"))
        painter.drawEllipse(badge)
        painter.setPen(QColor("#f2e5b4"))
        painter.setFont(QFont("Segoe UI", 7, QFont.Bold))
        painter.drawText(badge, Qt.AlignCenter, str(level))


class LevelGemChains(CompactGemChains):
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
                row.addWidget(LevelGemIcon(gem))
            row.addStretch()
            self.layout.addWidget(row_widget)
        self.layout.addStretch()
