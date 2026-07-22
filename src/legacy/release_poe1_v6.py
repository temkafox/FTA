"""Current release with explicit completed/next leveling route."""

from __future__ import annotations

import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication, QLabel

import main as legacy
import release_poe1_v5 as previous
from poe1_stage_logic import previous_stage
from poe1_target_widgets import leveling_stage
from poe1_tree_fast import ConstructionTreePlaceholder as LevelingRouteTreeCanvas


from actpilot.build_dialog import RouteBuildDialog


from actpilot.overlay import RouteOverlay


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setApplicationName(legacy.APP_NAME)
    app.setApplicationDisplayName(legacy.APP_NAME + " — PoE 1")
    legacy.ensure_cormorant_loaded()
    app.setFont(QFont("Segoe UI", 10))
    window = RouteOverlay()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
