"""PoE 1 leveling UI aligned with the target planner reference."""

from __future__ import annotations

import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication, QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

import main as legacy
import main_poe1 as base
import main_poe1_enhanced as enhanced
from poe1_target_widgets import DescribedGemLinksView, DetailedPassiveTreeCanvas, leveling_stage


from actpilot.build_dialog import TargetBuildProgressDialog


from actpilot.overlay import TargetPoe1Overlay


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setApplicationName(legacy.APP_NAME)
    app.setApplicationDisplayName(legacy.APP_NAME + " — PoE 1")
    legacy.ensure_cormorant_loaded()
    app.setFont(QFont("Segoe UI", 10))
    window = TargetPoe1Overlay()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
