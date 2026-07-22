"""PoE 1 release without granted non-gems or gem levels in tooltips."""

from __future__ import annotations

import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication

import main as legacy
import release_poe1_v20 as previous
from poe1_gem_widgets_v4 import CleanArtworkGemChains


from actpilot.build_dialog import SocketedGemBuildDialog


from actpilot.overlay import SocketedGemOverlay


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setApplicationName(legacy.APP_NAME)
    app.setApplicationDisplayName(legacy.APP_NAME + " — PoE 1 CLEAN")
    legacy.ensure_cormorant_loaded()
    app.setFont(QFont("Segoe UI", 10))
    window = SocketedGemOverlay()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
