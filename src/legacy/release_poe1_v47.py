"""PoE 1 fast tree with fixed manual selection and reliable window opacity."""

from __future__ import annotations

import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication

import main as legacy
import release_poe1_v41 as editor_release
import release_poe1_v46 as previous
from poe1_manual_editor_v6 import ManualBuildEditor


from actpilot.build_dialog import FixedInteractionBuildDialog


from actpilot.overlay import FixedInteractionOverlay


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setApplicationName(legacy.APP_NAME)
    app.setApplicationDisplayName(legacy.APP_NAME + " — PoE 1")
    legacy.ensure_cormorant_loaded()
    app.setFont(QFont("Segoe UI", 10))
    window = FixedInteractionOverlay()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
