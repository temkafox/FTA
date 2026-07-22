"""Current manual-editor release with safe existing-build loading."""

from __future__ import annotations

import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication, QPushButton

import main as legacy
import release_poe1_v36 as previous
from poe1_manual_editor_v3 import ManualBuildEditor
from release_poe1_v37 import _layout_with_widget


from actpilot.build_dialog import EditableBuildDialog


from actpilot.overlay import EditableBuildOverlay


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setApplicationName(legacy.APP_NAME)
    app.setApplicationDisplayName(legacy.APP_NAME + " — PoE 1")
    legacy.ensure_cormorant_loaded()
    app.setFont(QFont("Segoe UI", 10))
    window = EditableBuildOverlay()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
