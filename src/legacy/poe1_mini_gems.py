"""Minimal transparent gem-link preview for the main PoE 1 overlay."""

from __future__ import annotations

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QColor, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import QApplication, QToolTip, QWidget

from poe1_builds import stage_for_level
from poe1_gem_widgets_v3 import ICON_DIR, ICON_INDEX
from poe1_gem_widgets_v4 import GRANTED_NON_GEMS
from poe1_widgets import GEM_COLORS, infer_gem_color


class MiniGemLinks(QWidget):
    ICON = 22.0
    STEP_X = 29.0
    STEP_Y = 27.0
    MARGIN = 3.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setStyleSheet("""
            background: transparent;
            QToolTip {
                color: #eadfca;
                background: #080806;
                border: 1px solid #8a6937;
                padding: 4px 7px;
            }
        """)
        self._links = []
        self._items = []
        self._pixmaps = {}
        self._hovered = None
        self.setFixedSize(1, 1)

    @staticmethod
    def _clean_links(links):
        result = []
        for link in links or []:
            gems = [
                gem for gem in link.get("gems", [])
                if (gem.get("name") or "").casefold() not in GRANTED_NON_GEMS
            ]
            if gems:
                result.append(gems)
        return result

    def set_build_level(self, build, level):
        stage = stage_for_level((build or {}).get("gem_sets", []), level)
        self._links = self._clean_links(stage.get("links", [])) if stage else []
        self._items = []
        self._hovered = None
        if not self._links:
            self.setFixedSize(1, 1)
            self.setVisible(False)
            self.update()
            return
        longest = max(len(link) for link in self._links)
        width = int(self.MARGIN * 2 + self.ICON + max(0, longest - 1) * self.STEP_X)
        height = int(self.MARGIN * 2 + self.ICON + max(0, len(self._links) - 1) * self.STEP_Y)
        self.setFixedSize(max(28, width), max(28, height))
        self.setVisible(True)
        self.update()

    def _gem_pixmap(self, gem):
        name = (gem.get("name") or "").casefold()
        if name not in self._pixmaps:
            info = ICON_INDEX.get(name, {})
            self._pixmaps[name] = (
                QPixmap(str(ICON_DIR / info.get("file", ""))) if info else QPixmap()
            )
        return self._pixmaps[name]

    def _layout_items(self):
        rows = []
        items = []
        for row_index, gems in enumerate(self._links):
            y = self.MARGIN + row_index * self.STEP_Y
            row = []
            for column, gem in enumerate(gems):
                x = self.MARGIN + column * self.STEP_X
                rect = QRectF(x, y, self.ICON, self.ICON)
                row.append((gem, rect))
                items.append((gem, rect))
            rows.append(row)
        self._items = items
        return rows

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        rows = self._layout_items()
        painter.setPen(QPen(QColor(199, 151, 56, 185), 1.2, Qt.SolidLine, Qt.RoundCap))
        for row in rows:
            for (_, first), (_, second) in zip(row, row[1:]):
                painter.drawLine(
                    QPointF(first.right() + 1.0, first.center().y()),
                    QPointF(second.left() - 1.0, second.center().y()),
                )
        for row in rows:
            for gem, rect in row:
                pixmap = self._gem_pixmap(gem)
                if not pixmap.isNull():
                    painter.drawPixmap(rect, pixmap, QRectF(pixmap.rect()))
                    continue
                color_name = infer_gem_color(gem.get("name", ""))
                dark, light = GEM_COLORS.get(color_name, GEM_COLORS["white"])
                painter.setBrush(dark)
                painter.setPen(QPen(light, 1.0))
                painter.drawEllipse(rect.adjusted(2, 2, -2, -2))
        painter.end()

    def _gem_at(self, point):
        for gem, rect in self._items:
            if rect.adjusted(-2, -2, 2, 2).contains(point):
                return gem
        return None

    def mouseMoveEvent(self, event):
        gem = self._gem_at(event.pos())
        name = (gem.get("name") or "").strip() if gem else ""
        if name != self._hovered:
            self._hovered = name or None
            if name:
                QToolTip.showText(event.globalPos(), name, self)
            else:
                QToolTip.hideText()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self._hovered = None
        QToolTip.hideText()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            gem = self._gem_at(event.pos())
            name = (gem.get("name") or "").strip() if gem else ""
            if name:
                QApplication.clipboard().setText(name)
                QToolTip.showText(event.globalPos(), f"Скопировано: {name}", self)
                event.accept()
                return
        super().mousePressEvent(event)

