"""Opaque PoE tooltip with exact selected mastery effects from PoB."""

from __future__ import annotations

import html
import math
import re

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPainter, QPen
from PyQt5.QtWidgets import QApplication, QFrame

from poe1_tree_renderer_v2 import PoePassiveTooltip
from poe1_tree_renderer_v3 import ConnectedPassiveTreeCanvas
from poe1_widgets import PassiveTreeCanvas


MASTERY_PAIR = re.compile(r"\{\s*(\d+)\s*,\s*(\d+)\s*\}")


def parse_mastery_selection(raw: str) -> dict[str, int]:
    return {node_id: int(effect_id) for node_id, effect_id in MASTERY_PAIR.findall(raw or "")}


class OpaqueMasteryTooltip(PoePassiveTooltip):
    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor("#050505"))
        self.setPalette(palette)
        self.setWindowOpacity(1.0)

    def show_mastery(self, node, selected, effect_id, global_pos):
        self.title.setText(node.get("name") or "Mastery")
        chosen = next(
            (effect for effect in node.get("masteryEffects", []) if int(effect.get("effect", -1)) == effect_id),
            None,
        )
        if chosen:
            self.kind.setText("МАСТЕРСТВО ВЗЯТО · ЭФФЕКТ ИЗ БИЛДА")
            values = chosen.get("stats", [])
            color = "#8ca5ff"
        elif selected:
            self.kind.setText("МАСТЕРСТВО ВЗЯТО · ЭФФЕКТ НЕ УДАЛОСЬ СОПОСТАВИТЬ")
            values = []
            color = "#d6a35f"
        else:
            self.kind.setText("МАСТЕРСТВО НЕ ВЗЯТО")
            values = []
            color = "#888888"
        lines = [html.escape(str(value)).replace("\n", "<br>") for value in values]
        self.stats.setStyleSheet(f"color:{color};")
        self.stats.setText("<br>".join(lines) or "В сохранённом билде нет выбранного эффекта")
        self._place(global_pos)

    def show_regular(self, node, selected, global_pos):
        self.stats.setStyleSheet("color:#8ca5ff;")
        super().show_node(node, selected, global_pos)

    def _place(self, global_pos):
        self.adjustSize()
        screen = QApplication.screenAt(global_pos)
        geometry = screen.availableGeometry() if screen else QApplication.primaryScreen().availableGeometry()
        x, y = global_pos.x() + 18, global_pos.y() + 18
        if x + self.width() > geometry.right():
            x = global_pos.x() - self.width() - 18
        if y + self.height() > geometry.bottom():
            y = global_pos.y() - self.height() - 18
        self.move(max(geometry.left(), x), max(geometry.top(), y))
        self.show()
        self.raise_()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#050505"))
        painter.setPen(QPen(QColor("#80643c"), 2))
        painter.drawRect(self.rect().adjusted(1, 1, -2, -2))
        painter.setPen(QPen(QColor("#c0a16b"), 1))
        length = 13
        for x, sx in ((3, 1), (self.width() - 4, -1)):
            for y, sy in ((3, 1), (self.height() - 4, -1)):
                painter.drawLine(x, y, x + sx * length, y)
                painter.drawLine(x, y, x, y + sy * length)
                painter.drawLine(x + sx * 4, y + sy * 4, x + sx * 10, y + sy * 4)
                painter.drawLine(x + sx * 4, y + sy * 4, x + sx * 4, y + sy * 10)


class MasteryAwareTreeCanvas(ConnectedPassiveTreeCanvas):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.node_tooltip.hide()
        self.node_tooltip.deleteLater()
        self.node_tooltip = OpaqueMasteryTooltip()
        self.selected_masteries = {}

    def set_masteries(self, raw: str):
        self.selected_masteries = parse_mastery_selection(raw)

    def mouseMoveEvent(self, event):
        if self._drag_start is not None:
            self.node_tooltip.hide()
            return PassiveTreeCanvas.mouseMoveEvent(self, event)
        node_id = self._node_at(event)
        if not node_id:
            self.node_tooltip.hide()
            return
        node = self.nodes.get(node_id, {})
        if node.get("isMastery"):
            self.node_tooltip.show_mastery(
                node,
                node_id in self.selected,
                self.selected_masteries.get(node_id),
                event.globalPos(),
            )
        else:
            self.node_tooltip.show_regular(node, node_id in self.selected, event.globalPos())
