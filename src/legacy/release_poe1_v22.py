"""PoE 1 release with a separate ascendancy progression tab."""

from __future__ import annotations

import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication, QTabWidget, QVBoxLayout, QWidget

import main as legacy
import release_poe1_v21 as previous
from poe1_ascendancy_widget import AscendancyProgressWidget


from actpilot.build_dialog import AscendancyBuildDialog


from actpilot.overlay import AscendancyOverlay


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setApplicationName(legacy.APP_NAME)
    app.setApplicationDisplayName(legacy.APP_NAME + " — PoE 1 CLEAN")
    legacy.ensure_cormorant_loaded()
    app.setFont(QFont("Segoe UI", 10))
    window = AscendancyOverlay()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
