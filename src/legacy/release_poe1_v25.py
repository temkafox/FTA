"""PoE 1 release with ascendancy highlighted in its native tree location."""

from __future__ import annotations

import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication, QPushButton

import main as legacy
import main_poe1 as base
import release_poe1_v24 as previous
from poe1_tree_fast import ConstructionTreePlaceholder as NativeAscendancyTreeCanvas


from actpilot.build_dialog import NativeAscendancyBuildDialog


from actpilot.overlay import NativeAscendancyOverlay


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setApplicationName(legacy.APP_NAME)
    app.setApplicationDisplayName(legacy.APP_NAME + " — PoE 1 CLEAN")
    legacy.ensure_cormorant_loaded()
    app.setFont(QFont("Segoe UI", 10))
    window = NativeAscendancyOverlay()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
