"""PoE 1 release with passive snapshots and fixed always-on-top combo popups."""

from __future__ import annotations

import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication

import main as legacy
import release_poe1_v39 as manual_renderer
import release_poe1_v41 as editor_release
import release_poe1_v47 as previous
from poe1_manual_editor_v7 import ManualBuildEditor
from poe1_manual_plan_v2 import manual_passive_plan


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setApplicationName(legacy.APP_NAME)
    app.setApplicationDisplayName(legacy.APP_NAME + " — PoE 1")
    legacy.ensure_cormorant_loaded()
    app.setFont(QFont("Segoe UI", 10))
    window = previous.FixedInteractionOverlay()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
