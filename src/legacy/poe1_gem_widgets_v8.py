"""PoEDB-enriched Russian gem tooltips with English gem names."""

from __future__ import annotations

import html

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCursor, QFont
from PyQt5.QtWidgets import QApplication, QLabel, QWidget

from actpilot.data_cache import game_data
from poe1_gem_widgets_v7 import AcquisitionGemChains, AcquisitionGemIcon, AcquisitionGemTooltip


POEDB_GEMS = game_data("poedb_gems_ru.json")


def _rich(lines, color="#9b9cff"):
    clean = [str(line).strip() for line in lines if str(line).strip()]
    return "<br>".join(
        f'<span style="color:{color}">{html.escape(line)}</span>' for line in clean
    )


class PoedbGemTooltip(AcquisitionGemTooltip):
    def __init__(self):
        super().__init__()
        self.setFixedWidth(520)
        self.poedb_details = QLabel()
        self.poedb_details.setTextFormat(Qt.RichText)
        self.poedb_details.setWordWrap(True)
        self.poedb_details.setAlignment(Qt.AlignCenter)
        self.poedb_details.setFont(QFont("Georgia", 10))
        self.poedb_details.setStyleSheet(
            "color:#9b9cff; border-top:1px solid #263a35; padding-top:7px;"
        )
        layout = self.layout()
        layout.removeWidget(self.acquisition)
        layout.addWidget(self.poedb_details)
        layout.addWidget(self.acquisition)

    def show_acquisition(self, gem, class_name, global_pos):
        super().show_acquisition(gem, class_name, global_pos)
        data = POEDB_GEMS.get((gem.get("name") or "").casefold())
        if data:
            kind = "КАМЕНЬ ПОДДЕРЖКИ" if gem.get("support") else "АКТИВНЫЙ КАМЕНЬ"
            tags = data.get("tags") or kind
            self.meta.setText(tags.upper())
            description = data.get("description") or ""
            self.description.setText(html.escape(description).replace("\n", "<br>"))
            lines = []
            lines.extend(data.get("properties") or [])
            lines.extend(data.get("requirements") or [])
            lines.extend(data.get("modifiers") or [])
            lines.extend(data.get("reminders") or [])
            if data.get("quality"):
                lines.append("Дополнительные эффекты от качества:")
                lines.extend(data["quality"])
            self.poedb_details.setText(_rich(lines))
            self.poedb_details.show()
        else:
            self.poedb_details.setText(
                '<span style="color:#777f7b">Подробные данные PoEDB ещё не загружены.</span>'
            )
            self.poedb_details.show()
        self.adjustSize()
        screen = QApplication.screenAt(global_pos)
        geometry = screen.availableGeometry() if screen else QApplication.primaryScreen().availableGeometry()
        x, y = global_pos.x() + 16, global_pos.y() + 16
        if x + self.width() > geometry.right():
            x = global_pos.x() - self.width() - 16
        if y + self.height() > geometry.bottom():
            y = global_pos.y() - self.height() - 16
        self.move(max(geometry.left(), x), max(geometry.top(), y))


class PoedbGemIcon(AcquisitionGemIcon):
    tooltip_poedb = None

    def __init__(self, gem, class_name, parent=None):
        super().__init__(gem, class_name, parent)
        if PoedbGemIcon.tooltip_poedb is None:
            PoedbGemIcon.tooltip_poedb = PoedbGemTooltip()

    def enterEvent(self, event):
        PoedbGemIcon.tooltip_poedb.show_acquisition(
            self.gem, self.character_class, QCursor.pos(),
        )
        QWidget.enterEvent(self, event)

    def leaveEvent(self, event):
        PoedbGemIcon.tooltip_poedb.hide()
        QWidget.leaveEvent(self, event)


class PoedbGemChains(AcquisitionGemChains):
    icon_class = PoedbGemIcon

    def set_links(self, title, links):
        links = self._socketed_links(links)
        while self.layout.count():
            item = self.layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        from PyQt5.QtWidgets import QHBoxLayout

        heading = QLabel(title)
        heading.setAlignment(Qt.AlignCenter)
        heading.setFont(QFont("Segoe UI", 11, QFont.DemiBold))
        heading.setStyleSheet(
            "color:#e5dfd1; padding:6px; border-bottom:1px solid rgba(154,116,57,.32);"
        )
        self.layout.addWidget(heading)
        for link in links:
            row_widget = QWidget()
            row_widget.setStyleSheet("background:transparent;")
            row = QHBoxLayout(row_widget)
            row.setContentsMargins(8, 2, 0, 2)
            row.setSpacing(1)
            for index, gem in enumerate(link.get("gems", [])):
                if index:
                    connector = QLabel("—")
                    connector.setFixedWidth(14)
                    connector.setAlignment(Qt.AlignCenter)
                    connector.setStyleSheet("color:rgba(205,165,92,.62); font-size:17px;")
                    row.addWidget(connector)
                row.addWidget(self.icon_class(gem, self.character_class))
            row.addStretch()
            self.layout.addWidget(row_widget)
        self.layout.addStretch()
