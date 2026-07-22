"""Current PoE 1 release with strict one-node-per-level progression."""

from __future__ import annotations

import sys

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication

import main as legacy
import release_poe1_v13 as previous
from poe1_level_plan_v4 import strict_passive_plan
from release_poe1_v8 import TREE_GRAPH


from actpilot.build_dialog import StrictProgressionBuildDialog


from actpilot.overlay import StrictProgressionOverlay


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setApplicationName(legacy.APP_NAME)
    app.setApplicationDisplayName(legacy.APP_NAME + " — PoE 1 CURRENT")
    legacy.ensure_cormorant_loaded()
    app.setFont(QFont("Segoe UI", 10))
    window = StrictProgressionOverlay()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
