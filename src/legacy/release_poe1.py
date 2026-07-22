"""Current release entry for the PoE 1 ActPilot prototype."""

from __future__ import annotations

import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication

import main as legacy
import main_poe1_corrected as corrected
from poe1_mastery_tree import CompleteTooltipTreeCanvas


from actpilot.build_dialog import ReleaseBuildDialog


from actpilot.overlay import ReleaseOverlay


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setApplicationName(legacy.APP_NAME)
    app.setApplicationDisplayName(legacy.APP_NAME + " — PoE 1")
    legacy.ensure_cormorant_loaded()
    app.setFont(QFont("Segoe UI", 10))
    window = ReleaseOverlay()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
