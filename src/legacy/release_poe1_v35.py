"""PoE 1 polish: visible build button, Client.txt setting and PoEDB gem details."""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt5.QtCore import QPointF, QSize, Qt
from PyQt5.QtGui import QColor, QFont, QIcon, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import (
    QApplication, QDialog, QFileDialog, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QScrollArea, QWidget,
)

import main as legacy
import release_poe1_v34 as previous
from actpilot.gems.widgets import FallbackPoedbGemChains as PoedbGemChains
from actpilot.clientmonitor import find_client_log


def build_tree_icon(size=22):
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    gold = QColor("#c9a35a")
    painter.setPen(QPen(gold, 1.5))
    points = [QPointF(size * .50, size * .22), QPointF(size * .25, size * .70), QPointF(size * .75, size * .70)]
    painter.drawLine(points[0], points[1])
    painter.drawLine(points[0], points[2])
    painter.drawLine(points[1], points[2])
    painter.setBrush(QColor("#18150f"))
    for point in points:
        painter.drawEllipse(point, 2.8, 2.8)
    painter.end()
    return QIcon(pixmap)


from actpilot.build_dialog import PolishedBuildDialog


from actpilot.overlay import PolishedOverlay
from actpilot.settings_dialog import UpdateSettingsDialog

# Патч app.py (settings_release.Poe1SettingsDialog = UpdateSettingsDialog)
# материализован: _settings живёт в actpilot.overlay, где имя и резолвится.
Poe1SettingsDialog = UpdateSettingsDialog


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setApplicationName(legacy.APP_NAME)
    app.setApplicationDisplayName(legacy.APP_NAME + " — PoE 1")
    legacy.ensure_cormorant_loaded()
    app.setFont(QFont("Segoe UI", 10))
    window = PolishedOverlay()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
