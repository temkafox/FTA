"""Real gem artwork with clean tooltips and granted-skill filtering."""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCursor

from poe1_combined_widgets import GemDetailTooltip
from poe1_gem_widgets_v3 import ArtworkGemChains, ArtworkGemIcon


# PoB can expose skills granted by ascendancy/passive nodes in the same XML
# section as socketed gems. They are not gems and must not appear in links.
GRANTED_NON_GEMS = {
    "primal aegis",
}


class CleanGemDetailTooltip(GemDetailTooltip):
    def show_gem(self, gem, global_pos):
        super().show_gem(gem, global_pos)
        kind = "КАМЕНЬ ПОДДЕРЖКИ" if gem.get("support") else "АКТИВНЫЙ КАМЕНЬ"
        quality = gem.get("quality") or "0"
        self.meta.setText(f"{kind} · КАЧЕСТВО +{quality}%")
        self.adjustSize()


class CleanArtworkGemIcon(ArtworkGemIcon):
    tooltip = None

    def __init__(self, gem, parent=None):
        super().__init__(gem, parent)
        if CleanArtworkGemIcon.tooltip is None:
            CleanArtworkGemIcon.tooltip = CleanGemDetailTooltip()

    def enterEvent(self, event):
        CleanArtworkGemIcon.tooltip.show_gem(self.gem, QCursor.pos())
        super(ArtworkGemIcon, self).enterEvent(event)

    def leaveEvent(self, event):
        CleanArtworkGemIcon.tooltip.hide()
        super(ArtworkGemIcon, self).leaveEvent(event)


class CleanArtworkGemChains(ArtworkGemChains):
    @staticmethod
    def _socketed_links(links):
        result = []
        for link in links:
            gems = [
                gem for gem in link.get("gems", [])
                if (gem.get("name") or "").casefold() not in GRANTED_NON_GEMS
            ]
            if gems:
                clean = dict(link)
                clean["gems"] = gems
                result.append(clean)
        return result

    def set_links(self, title, links):
        links = self._socketed_links(links)
        while self.layout.count():
            item = self.layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        from PyQt5.QtGui import QFont
        from PyQt5.QtWidgets import QHBoxLayout, QLabel, QWidget

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
                row.addWidget(CleanArtworkGemIcon(gem))
            row.addStretch()
            self.layout.addWidget(row_widget)
        self.layout.addStretch()
