"""PoE 1 release with exact character-level gem scaling."""

from __future__ import annotations

import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication

import main as legacy
import release_poe1_v9 as previous
from poe1_gem_progression import links_at_level
from poe1_level_plan_v2 import stage_at_level


from actpilot.build_dialog import ScaledGemBuildDialog


from actpilot.overlay import ScaledGemOverlay


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setApplicationName(legacy.APP_NAME)
    app.setApplicationDisplayName(legacy.APP_NAME + " — PoE 1")
    legacy.ensure_cormorant_loaded()
    app.setFont(QFont("Segoe UI", 10))
    window = ScaledGemOverlay()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
