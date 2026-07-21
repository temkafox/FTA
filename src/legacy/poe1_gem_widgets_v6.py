"""Overlay-styled real gem links with Russian bodies and English names."""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCursor, QFont
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QWidget

from poe1_gem_widgets_v5 import CopyableArtworkGemIcon, CopyableGemChains
from poe1_tooltips_ru import RussianGemTooltip


class RussianCopyableGemIcon(CopyableArtworkGemIcon):
    tooltip_ru = None

    def __init__(self, gem, parent=None):
        super().__init__(gem, parent)
        if RussianCopyableGemIcon.tooltip_ru is None:
            RussianCopyableGemIcon.tooltip_ru = RussianGemTooltip()

    def enterEvent(self, event):
        RussianCopyableGemIcon.tooltip_ru.show_gem(self.gem, QCursor.pos())
        QWidget.enterEvent(self, event)

    def leaveEvent(self, event):
        RussianCopyableGemIcon.tooltip_ru.hide()
        QWidget.leaveEvent(self, event)


class RussianOverlayGemChains(CopyableGemChains):
    def set_links(self, title, links):
        links = self._socketed_links(links)
        while self.layout.count():
            item = self.layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        heading = QLabel(title)
        heading.setAlignment(Qt.AlignCenter)
        heading.setFont(QFont("Segoe UI", 11, QFont.DemiBold))
        heading.setStyleSheet(
            "color:#ffffff; padding:8px; border-bottom:2px solid #4ade80; background:#222228;"
        )
        self.layout.addWidget(heading)
        for link in links:
            row_widget = QWidget()
            row_widget.setStyleSheet("background:transparent;")
            row = QHBoxLayout(row_widget)
            row.setContentsMargins(12, 2, 0, 2)
            row.setSpacing(1)
            for index, gem in enumerate(link.get("gems", [])):
                if index:
                    connector = QLabel("—")
                    connector.setFixedWidth(14)
                    connector.setAlignment(Qt.AlignCenter)
                    connector.setStyleSheet("color:rgba(255,255,255,0.4); font-size:17px;")
                    row.addWidget(connector)
                row.addWidget(RussianCopyableGemIcon(gem))
            row.addStretch()
            self.layout.addWidget(row_widget)
        self.layout.addStretch()
