"""Current PoE 1 release with corrected key-node branch ordering."""

from __future__ import annotations

import sys

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication

import main as legacy
import release_poe1_v18 as previous
from poe1_level_plan_v9 import corrected_semantic_plan
from release_poe1_v8 import TREE_GRAPH


from actpilot.build_dialog import CorrectedSemanticBuildDialog


from actpilot.overlay import CorrectedSemanticOverlay


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setApplicationName(legacy.APP_NAME)
    app.setApplicationDisplayName(legacy.APP_NAME + " — PoE 1 CURRENT")
    legacy.ensure_cormorant_loaded()
    app.setFont(QFont("Segoe UI", 10))
    window = CorrectedSemanticOverlay()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
