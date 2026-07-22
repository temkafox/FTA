"""Compact ActPilot-styled PoE 1 build window with a level slider."""

from __future__ import annotations

import sys

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication, QLabel, QPushButton, QSlider

import main as legacy
import release_poe1_v32 as previous
from poe1_builds import clamp_level


from actpilot.build_dialog import CompactBuildDialog


from actpilot.overlay import CompactBuildOverlay


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setApplicationName(legacy.APP_NAME)
    app.setApplicationDisplayName(legacy.APP_NAME + " — PoE 1")
    legacy.ensure_cormorant_loaded()
    app.setFont(QFont("Segoe UI", 10))
    window = CompactBuildOverlay()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
