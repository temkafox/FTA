"""Current PoE 1 release: level points plus quest books, no bandits."""

from __future__ import annotations

import sys

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication, QLabel

import main as legacy
import release_poe1_v15 as previous
from poe1_level_plan_v6 import book_only_passive_plan
from release_poe1_v8 import TREE_GRAPH


from actpilot.build_dialog import BookOnlyBuildDialog


from actpilot.overlay import BookOnlyOverlay


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setApplicationName(legacy.APP_NAME)
    app.setApplicationDisplayName(legacy.APP_NAME + " — PoE 1 BOOKS")
    legacy.ensure_cormorant_loaded()
    app.setFont(QFont("Segoe UI", 10))
    window = BookOnlyOverlay()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
