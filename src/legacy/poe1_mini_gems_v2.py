"""Minimal gem links with the active level range above the icons."""

from __future__ import annotations

from PyQt5.QtCore import QRectF, Qt
from PyQt5.QtGui import QColor, QFont, QPainter

from poe1_builds import stage_for_level
from poe1_mini_gems import MiniGemLinks as BaseMiniGemLinks


class MiniGemLinks(BaseMiniGemLinks):
    HEADER_H = 15.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self._range_label = ""

    @staticmethod
    def _range_for(stages, active):
        stages = sorted(stages or [], key=lambda item: int(item.get("level", 1)))
        if not active or not stages:
            return ""
        index = next((i for i, stage in enumerate(stages) if stage is active), -1)
        if index < 0:
            active_level = int(active.get("level", 1))
            index = next(
                (i for i, stage in enumerate(stages) if int(stage.get("level", 1)) == active_level),
                0,
            )
        start = int(stages[index].get("level", 1))
        if index + 1 < len(stages):
            return f"{start}–{int(stages[index + 1].get('level', 1)) - 1}"
        return f"{start}+"

    def set_build_level(self, build, level):
        stages = (build or {}).get("gem_sets", [])
        active = stage_for_level(stages, level)
        self._range_label = self._range_for(stages, active)
        super().set_build_level(build, level)
        if self._links:
            self.setFixedHeight(int(self.height() + self.HEADER_H))

    def _layout_items(self):
        rows = super()._layout_items()
        shifted = []
        items = []
        for row in rows:
            shifted_row = []
            for gem, rect in row:
                moved = QRectF(rect)
                moved.translate(0, self.HEADER_H)
                shifted_row.append((gem, moved))
                items.append((gem, moved))
            shifted.append(shifted_row)
        self._items = items
        return shifted

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self._range_label:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.TextAntialiasing)
        painter.setFont(QFont("Segoe UI", 8, QFont.DemiBold))
        painter.setPen(QColor("#d7b86a"))
        painter.drawText(
            QRectF(0, 0, self.width(), self.HEADER_H),
            Qt.AlignCenter,
            self._range_label,
        )
        painter.end()

