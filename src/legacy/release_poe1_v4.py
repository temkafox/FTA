"""Current release with opaque tooltips and exact PoB mastery selection."""

from __future__ import annotations

import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication

import main as legacy
import release_poe1_v3 as previous
from poe1_target_widgets import leveling_stage
from poe1_tree_fast import ConstructionTreePlaceholder as MasteryAwareTreeCanvas


from actpilot.build_dialog import MasteryBuildDialog


from actpilot.overlay import MasteryOverlay


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setApplicationName(legacy.APP_NAME)
    app.setApplicationDisplayName(legacy.APP_NAME + " — PoE 1")
    legacy.ensure_cormorant_loaded()
    app.setFont(QFont("Segoe UI", 10))
    window = MasteryOverlay()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
