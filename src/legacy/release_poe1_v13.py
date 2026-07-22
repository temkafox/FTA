"""Current PoE 1 release: level labels, corrected colors and immediate focus."""

from __future__ import annotations

import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication

import main as legacy
import release_poe1_v12 as previous
from poe1_tree_fast import ConstructionTreePlaceholder as ImmediateFocusTreeCanvas


from actpilot.build_dialog import ImmediateFocusBuildDialog


from actpilot.overlay import ImmediateFocusOverlay


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setApplicationName(legacy.APP_NAME)
    app.setApplicationDisplayName(legacy.APP_NAME + " — PoE 1 CURRENT")
    legacy.ensure_cormorant_loaded()
    app.setFont(QFont("Segoe UI", 10))
    window = ImmediateFocusOverlay()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
