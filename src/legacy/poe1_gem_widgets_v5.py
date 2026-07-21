"""Clean real-art gem links with click-to-copy and no infinity marker."""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCursor, QFont
from PyQt5.QtWidgets import QApplication, QHBoxLayout, QLabel, QToolTip, QWidget

from poe1_gem_widgets_v4 import CleanArtworkGemChains, CleanArtworkGemIcon


class CopyableArtworkGemIcon(CleanArtworkGemIcon):
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            name = (self.gem.get("name") or "").strip()
            if name:
                QApplication.clipboard().setText(name)
                QToolTip.showText(
                    QCursor.pos(), f"Скопировано: {name}", self, self.rect(), 1400
                )
            event.accept()
            return
        super().mousePressEvent(event)


class CopyableGemChains(CleanArtworkGemChains):
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
            "color:#dadada; padding-bottom:8px; border-bottom:2px solid #258de5;"
        )
        self.layout.addWidget(heading)
        for link in links:
            row_widget = QWidget()
            row_widget.setStyleSheet("background:transparent;")
            row = QHBoxLayout(row_widget)
            row.setContentsMargins(10, 0, 0, 0)
            row.setSpacing(1)
            for index, gem in enumerate(link.get("gems", [])):
                if index:
                    connector = QLabel("—")
                    connector.setFixedWidth(14)
                    connector.setAlignment(Qt.AlignCenter)
                    connector.setStyleSheet("color:#d89c44; font-size:17px;")
                    row.addWidget(connector)
                row.addWidget(CopyableArtworkGemIcon(gem))
            row.addStretch()
            self.layout.addWidget(row_widget)
        self.layout.addStretch()
