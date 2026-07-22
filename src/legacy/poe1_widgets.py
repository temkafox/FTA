"""Гем-виджеты и Client.txt-монитор; PassiveTreeCanvas переехал в actpilot.tree."""

from __future__ import annotations

import os
import re
from pathlib import Path

from PyQt5.QtCore import QPointF, Qt, QTimer, pyqtSignal, QObject
from PyQt5.QtGui import QColor, QFont, QPainter, QPen, QPolygonF
from PyQt5.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget,
)


LEVEL_PATTERN = re.compile(
    r":\s*(?P<name>[^\r\n:]+?)\s*\((?P<class>[^)]+)\)\s+is now level\s+(?P<level>\d{1,3})",
    re.IGNORECASE,
)


def find_client_log() -> Path | None:
    candidates = []
    for env_name in ("PROGRAMFILES(X86)", "PROGRAMFILES"):
        root = os.environ.get(env_name)
        if not root:
            continue
        candidates.extend(
            [
                Path(root) / "Grinding Gear Games" / "Path of Exile" / "logs" / "Client.txt",
                Path(root) / "Steam" / "steamapps" / "common" / "Path of Exile" / "logs" / "Client.txt",
            ]
        )
    documents = Path.home() / "Documents" / "My Games" / "Path of Exile" / "logs" / "Client.txt"
    candidates.append(documents)
    existing = [path for path in candidates if path.is_file()]
    return max(existing, key=lambda path: path.stat().st_mtime) if existing else None


def read_log_tail(path: Path, byte_count=2_000_000) -> str:
    try:
        with path.open("rb") as stream:
            stream.seek(0, os.SEEK_END)
            size = stream.tell()
            stream.seek(max(0, size - byte_count))
            return stream.read().decode("utf-8", errors="replace")
    except OSError:
        return ""


class ClientLevelMonitor(QObject):
    level_seen = pyqtSignal(str, str, int)
    status_changed = pyqtSignal(str)

    def __init__(self, parent=None, path: Path | None = None):
        super().__init__(parent)
        self.path = path or find_client_log()
        self._position = 0
        self._timer = QTimer(self)
        self._timer.setInterval(1500)
        self._timer.timeout.connect(self.poll)

    def start(self):
        if not self.path or not self.path.is_file():
            self.status_changed.emit("Client.txt не найден — уровень меняется кнопками −/+")
            return
        tail = read_log_tail(self.path)
        matches = list(LEVEL_PATTERN.finditer(tail))
        if matches:
            match = matches[-1]
            self.level_seen.emit(
                match.group("name").strip(), match.group("class").strip(), int(match.group("level"))
            )
        try:
            self._position = self.path.stat().st_size
        except OSError:
            self._position = 0
        self.status_changed.emit(f"Уровень синхронизируется: {self.path}")
        self._timer.start()

    def poll(self):
        if not self.path:
            return
        try:
            size = self.path.stat().st_size
            if size < self._position:
                self._position = 0
            if size == self._position:
                return
            with self.path.open("rb") as stream:
                stream.seek(self._position)
                chunk = stream.read()
                self._position = stream.tell()
            text = chunk.decode("utf-8", errors="replace")
        except OSError:
            return
        for match in LEVEL_PATTERN.finditer(text):
            self.level_seen.emit(
                match.group("name").strip(), match.group("class").strip(), int(match.group("level"))
            )


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
            self.layout.addWidget(QLabel("На этом этапе связки не найдены."))
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
