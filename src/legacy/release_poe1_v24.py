"""PoE 1 release with ascendancy integrated into the main tree and copyable gems."""

from __future__ import annotations

import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication

import main as legacy
import release_poe1_v23 as previous
from poe1_gem_widgets_v5 import CopyableGemChains
from poe1_tree_fast import ConstructionTreePlaceholder as IntegratedAscendancyTreeCanvas


from actpilot.build_dialog import IntegratedTreeBuildDialog


from actpilot.overlay import IntegratedTreeOverlay


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setApplicationName(legacy.APP_NAME)
    app.setApplicationDisplayName(legacy.APP_NAME + " — PoE 1 CLEAN")
    legacy.ensure_cormorant_loaded()
    app.setFont(QFont("Segoe UI", 10))
    window = IntegratedTreeOverlay()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
