"""PoE 1 release: nearest connected route, Russian bodies, overlay styling."""

from __future__ import annotations

import sys

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication

import main as legacy
import release_poe1_v26 as previous
from poe1_gem_widgets_v6 import RussianOverlayGemChains
from poe1_level_plan_v11 import ordinary_nearest_plan as nearest_connected_plan
from poe1_tree_fast import ConstructionTreePlaceholder as RussianDescriptionTreeCanvas
from release_poe1_v8 import TREE_GRAPH


from actpilot.build_dialog import LocalizedOverlayBuildDialog


from actpilot.overlay import LocalizedOverlay


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setApplicationName(legacy.APP_NAME)
    app.setApplicationDisplayName(legacy.APP_NAME + " — PoE 1")
    legacy.ensure_cormorant_loaded()
    app.setFont(QFont("Segoe UI", 10))
    window = LocalizedOverlay()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
