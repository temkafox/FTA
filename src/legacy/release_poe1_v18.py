"""Current PoE 1 release with branch-local semantic passive ordering."""

from __future__ import annotations

import sys

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication

import main as legacy
import release_poe1_v17 as previous
from poe1_level_plan_v8 import semantic_book_passive_plan
from release_poe1_v8 import TREE_GRAPH


from actpilot.build_dialog import SemanticPassiveBuildDialog


from actpilot.overlay import SemanticPassiveOverlay


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setApplicationName(legacy.APP_NAME)
    app.setApplicationDisplayName(legacy.APP_NAME + " — PoE 1 SEMANTIC")
    legacy.ensure_cormorant_loaded()
    app.setFont(QFont("Segoe UI", 10))
    window = SemanticPassiveOverlay()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
