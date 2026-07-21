"""Real gem links with class-aware Q/B acquisition badges and tooltips."""

from __future__ import annotations

from PyQt5.QtCore import QRectF, Qt
from PyQt5.QtGui import QColor, QCursor, QFont, QPainter, QPen
from PyQt5.QtWidgets import QApplication, QHBoxLayout, QLabel, QWidget

from poe1_gem_acquisition import acquisition_html, badges_for
from poe1_gem_widgets_v6 import RussianCopyableGemIcon, RussianOverlayGemChains
from poe1_tooltips_ru import RussianGemTooltip


class AcquisitionGemTooltip(RussianGemTooltip):
    def __init__(self):
        super().__init__()
        self.acquisition = QLabel()
        self.acquisition.setTextFormat(Qt.RichText)
        self.acquisition.setWordWrap(True)
        self.acquisition.setAlignment(Qt.AlignLeft)
        self.acquisition.setFont(QFont("Segoe UI", 9))
        self.acquisition.setStyleSheet(
            "color:#d7dbe4; border-top:1px solid #334038; padding-top:8px;"
        )
        self.layout().addWidget(self.acquisition)

    def show_acquisition(self, gem, class_name, global_pos):
        super().show_gem(gem, global_pos)
        self.acquisition.setText(
            acquisition_html(gem.get("name"), class_name)
        )
        self.acquisition.show()
        self.adjustSize()
        screen = QApplication.screenAt(global_pos)
        geometry = screen.availableGeometry() if screen else QApplication.primaryScreen().availableGeometry()
        x, y = global_pos.x() + 16, global_pos.y() + 16
        if x + self.width() > geometry.right():
            x = global_pos.x() - self.width() - 16
        if y + self.height() > geometry.bottom():
            y = global_pos.y() - self.height() - 16
        self.move(max(geometry.left(), x), max(geometry.top(), y))


class AcquisitionGemIcon(RussianCopyableGemIcon):
    tooltip_acquisition = None

    def __init__(self, gem, class_name, parent=None):
        self.character_class = class_name
        super().__init__(gem, parent)
        if AcquisitionGemIcon.tooltip_acquisition is None:
            AcquisitionGemIcon.tooltip_acquisition = AcquisitionGemTooltip()

    def paintEvent(self, event):
        super().paintEvent(event)
        badges = badges_for(self.gem.get("name"), self.character_class)
        if not badges:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setFont(QFont("Segoe UI", 7, QFont.Bold))
        for index, letter in enumerate(badges):
            rect = QRectF(1 + index * 14, 29, 13, 13)
            color = QColor("#32df72") if letter == "Q" else QColor("#e1ae35")
            painter.setPen(QPen(QColor("#071009"), 1))
            painter.setBrush(color)
            painter.drawRoundedRect(rect, 4, 4)
            painter.setPen(QColor("#071009"))
            painter.drawText(rect, Qt.AlignCenter, letter)

    def enterEvent(self, event):
        AcquisitionGemIcon.tooltip_acquisition.show_acquisition(
            self.gem, self.character_class, QCursor.pos(),
        )
        QWidget.enterEvent(self, event)

    def leaveEvent(self, event):
        AcquisitionGemIcon.tooltip_acquisition.hide()
        QWidget.leaveEvent(self, event)


class AcquisitionGemChains(RussianOverlayGemChains):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.character_class = ""

    def set_character_class(self, class_name):
        self.character_class = class_name or ""

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
                row.addWidget(AcquisitionGemIcon(gem, self.character_class))
            row.addStretch()
            self.layout.addWidget(row_widget)
        self.layout.addStretch()
