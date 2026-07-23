"""Гем-виджеты и WindowDragHeader; монитор — в actpilot.clientmonitor, дерево — в actpilot.tree."""

from __future__ import annotations

from PyQt5.QtCore import QPointF, Qt
from PyQt5.QtGui import QColor, QFont, QPainter, QPen, QPolygonF
from PyQt5.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget,
)


class WindowDragHeader(QFrame):
    """Заголовок без рамки: тащит окно-владельца за смещение курсора."""

    def __init__(self, window, parent=None):
        super().__init__(parent if parent is not None else window)
        self._window = window
        self._drag_offset = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_offset = event.globalPos() - self._window.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_offset is not None and event.buttons() & Qt.LeftButton:
            self._window.move(event.globalPos() - self._drag_offset)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_offset = None
        super().mouseReleaseEvent(event)


def infer_gem_color(name: str) -> str:
    """Best-effort socket colour when PoB XML does not expose the attribute."""
    value = (name or "").lower()
    green = (
        "projectile", "arrow", "bow", "trap", "mine", "poison", "bleed", "cold",
        "frost", "ice", "critical", "accuracy", "evasion", "speed", "dexterity",
        "nightblade", "volley", "barrage", "swift", "chance to flee", "culling",
    )
    red = (
        "melee", "physical", "fire", "burn", "ignite", "strength", "armour", "stun",
        "fortify", "brutality", "rage", "slam", "warcry", "totem", "life", "blood",
        "multistrike", "ancestral", "maim", "impale",
    )
    blue = (
        "spell", "lightning", "chaos", "minion", "aura", "curse", "mana", "energy shield",
        "intelligence", "arcane", "elemental", "concentrated", "controlled destruction",
        "inspiration", "unleash", "echo", "penetration", "brand", "summon",
    )
    scores = {
        "green": sum(token in value for token in green),
        "red": sum(token in value for token in red),
        "blue": sum(token in value for token in blue),
    }
    return max(scores, key=scores.get) if max(scores.values()) else "blue"


GEM_COLORS = {
    "red": (QColor("#b72b2b"), QColor("#ff8a6e")),
    "green": (QColor("#16844a"), QColor("#77ef9d")),
    "blue": (QColor("#2465ad"), QColor("#84c8ff")),
    "white": (QColor("#a8a8a8"), QColor("#ffffff")),
}


class GemIcon(QWidget):
    def __init__(self, gem: dict, parent=None):
        super().__init__(parent)
        self.gem = gem
        self.color_name = gem.get("color") or infer_gem_color(gem.get("name", ""))
        self.setFixedSize(62, 62)
        self.setToolTip(gem.get("name", "Камень"))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        dark, light = GEM_COLORS.get(self.color_name, GEM_COLORS["white"])
        center = QPointF(self.width() / 2, self.height() / 2)
        if self.gem.get("support"):
            points = QPolygonF([
                QPointF(center.x(), 5), QPointF(56, 19), QPointF(50, 49),
                QPointF(center.x(), 58), QPointF(12, 49), QPointF(6, 19),
            ])
        else:
            points = QPolygonF([
                QPointF(center.x(), 4), QPointF(55, center.y()),
                QPointF(center.x(), 58), QPointF(7, center.y()),
            ])
        painter.setPen(QPen(light, 2))
        painter.setBrush(dark)
        painter.drawPolygon(points)
        inner = QPolygonF([
            QPointF(center.x(), 12), QPointF(46, center.y()),
            QPointF(center.x(), 50), QPointF(16, center.y()),
        ])
        painter.setPen(QPen(QColor(255, 255, 255, 90), 1))
        painter.setBrush(QColor(light.red(), light.green(), light.blue(), 70))
        painter.drawPolygon(inner)
        initial = (self.gem.get("name") or "?").strip()[:1].upper()
        painter.setPen(QColor("white"))
        painter.setFont(QFont("Segoe UI", 13, QFont.Bold))
        painter.drawText(self.rect(), Qt.AlignCenter, initial)


class GemCard(QFrame):
    def __init__(self, gem: dict, parent=None):
        super().__init__(parent)
        self.setFixedWidth(150)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(3)
        icon = GemIcon(gem)
        layout.addWidget(icon, 0, Qt.AlignHCenter)
        name = QLabel(gem.get("name", "Камень"))
        name.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        name.setWordWrap(True)
        name.setFixedHeight(38)
        name.setStyleSheet("color:#eeeeee;")
        layout.addWidget(name)


class GemLinksView(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.body = QWidget()
        self.layout = QVBoxLayout(self.body)
        self.layout.setContentsMargins(12, 12, 12, 12)
        self.layout.setSpacing(16)
        self.setWidget(self.body)

    def set_links(self, title: str, links: list[dict]):
        while self.layout.count():
            item = self.layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        heading = QLabel(title)
        heading.setFont(QFont("Segoe UI", 13, QFont.DemiBold))
        heading.setStyleSheet("color:white;")
        self.layout.addWidget(heading)
        if not links:
            empty = QLabel("На этом этапе связки не найдены.")
            empty.setStyleSheet("color:#918b80;")
            self.layout.addWidget(empty)
        for link in links:
            block = QFrame()
            block.setStyleSheet("QFrame{background:#202027;border:1px solid #34343d;border-radius:9px;}")
            vertical = QVBoxLayout(block)
            label = QLabel(link.get("label", "Связка"))
            label.setFont(QFont("Segoe UI", 11, QFont.DemiBold))
            label.setStyleSheet("color:#e6c477;border:none;background:transparent;")
            vertical.addWidget(label)
            row = QHBoxLayout()
            row.setSpacing(2)
            for index, gem in enumerate(link.get("gems", [])):
                if index:
                    connector = QLabel("—")
                    connector.setFixedWidth(22)
                    connector.setAlignment(Qt.AlignCenter)
                    connector.setStyleSheet("color:#d8b863;border:none;background:transparent;font-size:18px;")
                    row.addWidget(connector)
                row.addWidget(GemCard(gem))
            row.addStretch()
            vertical.addLayout(row)
            self.layout.addWidget(block)
        self.layout.addStretch()
