"""PoE 1: zoom-safe tree plus simplified level-centric gem editor."""

from __future__ import annotations

import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication

import main as legacy
import release_poe1_v40 as previous
from poe1_manual_editor_v11 import ManualBuildEditor
from actpilot.tree import CachedZoomSafeTreeCanvas as ZoomSafeTreeCanvas


from actpilot.build_dialog import ClearGemEditorBuildDialog


from actpilot.overlay import ClearGemEditorOverlay


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setApplicationName(legacy.APP_NAME)
    app.setApplicationDisplayName(legacy.APP_NAME + " — PoE 1")
    legacy.ensure_cormorant_loaded()
    app.setFont(QFont("Segoe UI", 10))
    window = ClearGemEditorOverlay()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
