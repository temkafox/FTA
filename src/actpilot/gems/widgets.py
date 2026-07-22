"""Живая цепочка гем-виджетов билд-окна: combined -> v3 -> v4 -> v5 -> v6 -> v7 -> v8 -> v9."""

from __future__ import annotations

import html

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import (
    QColor, QCursor, QFont, QPainter, QPainterPath, QPen, QPixmap,
    QRadialGradient,
)
from PyQt5.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QScrollArea, QToolTip,
    QVBoxLayout, QWidget,
)

from actpilot.data_cache import game_data
from actpilot.gems.data import acquisition_html, badges_for, gem_art_path
from actpilot.paths import get_resource_dir
from actpilot.ru_text import gem_description
from actpilot.base_widgets import GEM_COLORS, infer_gem_color


# Тот же кешированный объект, что и poe1_target_widgets.GEM_CATALOG (lru_cache в data_cache)
GEM_CATALOG = game_data("gem_catalog.json")


class GemDetailTooltip(QFrame):
    def __init__(self):
        super().__init__(None, Qt.ToolTip | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setAutoFillBackground(True)
        self.setWindowOpacity(1.0)
        self.setFixedWidth(470)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 13)
        layout.setSpacing(7)
        self.title = QLabel()
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setFont(QFont("Georgia", 14, QFont.DemiBold))
        self.title.setStyleSheet("color:#29d8c7; border-bottom:1px solid #497261; padding-bottom:7px;")
        layout.addWidget(self.title)
        self.meta = QLabel()
        self.meta.setAlignment(Qt.AlignCenter)
        self.meta.setFont(QFont("Georgia", 9))
        self.meta.setStyleSheet("color:#aaa69d;")
        layout.addWidget(self.meta)
        self.description = QLabel()
        self.description.setTextFormat(Qt.RichText)
        self.description.setWordWrap(True)
        self.description.setAlignment(Qt.AlignCenter)
        self.description.setFont(QFont("Georgia", 10))
        self.description.setStyleSheet("color:#28d8d0;")
        layout.addWidget(self.description)
        self.details = QLabel()
        self.details.setTextFormat(Qt.RichText)
        self.details.setWordWrap(True)
        self.details.setAlignment(Qt.AlignCenter)
        self.details.setFont(QFont("Georgia", 10))
        self.details.setStyleSheet("color:#9b9cff;")
        layout.addWidget(self.details)

    def show_gem(self, gem, global_pos):
        info = GEM_CATALOG.get((gem.get("name") or "").casefold(), {})
        name = gem.get("name") or "Камень"
        self.title.setText(name.upper())
        kind = "КАМЕНЬ ПОДДЕРЖКИ" if gem.get("support") else "АКТИВНЫЙ КАМЕНЬ"
        level = gem.get("level") or "—"
        quality = gem.get("quality") or "0"
        self.meta.setText(f"{kind} · УРОВЕНЬ {level} · КАЧЕСТВО +{quality}%")
        description = info.get("description") or "Описание отсутствует в данных Path of Building."
        self.description.setText(html.escape(description).replace("\n", "<br>"))
        color_name = info.get("color") or infer_gem_color(name)
        color_label = {"red": "СИЛА · КРАСНЫЙ", "green": "ЛОВКОСТЬ · ЗЕЛЁНЫЙ", "blue": "ИНТЕЛЛЕКТ · СИНИЙ", "white": "БЕЛЫЙ"}.get(color_name, color_name.upper())
        self.details.setText(color_label)
        self.adjustSize()
        screen = QApplication.screenAt(global_pos)
        geometry = screen.availableGeometry() if screen else QApplication.primaryScreen().availableGeometry()
        x, y = global_pos.x() + 16, global_pos.y() + 16
        if x + self.width() > geometry.right():
            x = global_pos.x() - self.width() - 16
        if y + self.height() > geometry.bottom():
            y = global_pos.y() - self.height() - 16
        self.move(max(geometry.left(), x), max(geometry.top(), y))
        self.show()
        self.raise_()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#040606"))
        painter.setPen(QPen(QColor("#476e5f"), 2))
        painter.drawRect(self.rect().adjusted(1, 1, -2, -2))
        painter.setPen(QPen(QColor("#85b6a1"), 1))
        for x, sx in ((3, 1), (self.width() - 4, -1)):
            for y, sy in ((3, 1), (self.height() - 4, -1)):
                painter.drawLine(x, y, x + sx * 14, y)
                painter.drawLine(x, y, x, y + sy * 14)


class CompactGemIcon(QWidget):
    tooltip = None

    def __init__(self, gem, parent=None):
        super().__init__(parent)
        self.gem = gem
        info = GEM_CATALOG.get((gem.get("name") or "").casefold(), {})
        self.color_name = info.get("color") or infer_gem_color(gem.get("name", ""))
        self.setFixedSize(43, 43)
        self.setCursor(Qt.PointingHandCursor)
        if CompactGemIcon.tooltip is None:
            CompactGemIcon.tooltip = GemDetailTooltip()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        dark, light = GEM_COLORS.get(self.color_name, GEM_COLORS["white"])
        center = QPointF(21.5, 21.5)
        painter.setPen(QPen(QColor("#a98542"), 2))
        painter.setBrush(QColor("#10151b"))
        painter.drawEllipse(center, 19, 19)
        gradient = QRadialGradient(center - QPointF(5, 6), 22)
        gradient.setColorAt(0, light)
        gradient.setColorAt(0.45, dark)
        gradient.setColorAt(1, QColor("#071018"))
        crystal = QPainterPath()
        if self.gem.get("support"):
            crystal.addRoundedRect(QRectF(9, 9, 25, 25), 7, 7)
        else:
            crystal.moveTo(21.5, 6)
            crystal.lineTo(36, 21.5)
            crystal.lineTo(21.5, 37)
            crystal.lineTo(7, 21.5)
            crystal.closeSubpath()
        painter.setBrush(gradient)
        painter.setPen(QPen(light, 1.2))
        painter.drawPath(crystal)
        painter.setPen(QColor("white"))
        painter.setFont(QFont("Segoe UI", 10, QFont.Bold))
        painter.drawText(self.rect(), Qt.AlignCenter, (self.gem.get("name") or "?")[:1].upper())

    def enterEvent(self, event):
        self.tooltip.show_gem(self.gem, QCursor.pos())
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.tooltip.hide()
        super().leaveEvent(event)


class CompactGemChains(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.body = QWidget()
        self.body.setStyleSheet("background:#08090b;")
        self.layout = QVBoxLayout(self.body)
        self.layout.setContentsMargins(14, 14, 10, 14)
        self.layout.setSpacing(14)
        self.setWidget(self.body)

    def set_links(self, title, links):
        while self.layout.count():
            item = self.layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        heading = QLabel(title)
        heading.setAlignment(Qt.AlignCenter)
        heading.setFont(QFont("Segoe UI", 11, QFont.DemiBold))
        heading.setStyleSheet("color:#dadada; padding-bottom:8px; border-bottom:2px solid #258de5;")
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
                row.addWidget(CompactGemIcon(gem))
            row.addStretch()
            self.layout.addWidget(row_widget)
        self.layout.addStretch()


# Прежде ROOT считался от __file__ модуля; get_resource_dir() даёт тот же каталог
ROOT = get_resource_dir() / "data" / "poe1"
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


class RussianGemTooltip(CleanGemDetailTooltip):
    def show_gem(self, gem, global_pos):
        super().show_gem(gem, global_pos)
        description = gem_description(gem.get("name"))
        if not description:
            description = "Русское описание этого камня пока отсутствует в локальных данных."
        self.description.setText(html.escape(description).replace("\n", "<br>"))
        self.details.clear()
        self.details.hide()
        self.adjustSize()


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


class FallbackPoedbGemIcon(PoedbGemIcon):
    def __init__(self, gem, class_name, parent=None):
        super().__init__(gem, class_name, parent)
        if self.art.isNull():
            path = gem_art_path(gem)
            self.art = QPixmap(str(path)) if path else QPixmap()


class FallbackPoedbGemChains(PoedbGemChains):
    icon_class = FallbackPoedbGemIcon


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
