"""PoE 1 release with immutable node coordinates during manual-tree panning."""

from __future__ import annotations

import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication

import main as legacy
import release_poe1_v41 as editor_release
import release_poe1_v48 as staged_release
import release_poe1_v49 as previous
from poe1_manual_editor_v9 import ManualBuildEditor


editor_release.ManualBuildEditor = ManualBuildEditor


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setApplicationName(legacy.APP_NAME)
    app.setApplicationDisplayName(legacy.APP_NAME + " — PoE 1")
    legacy.ensure_cormorant_loaded()
    app.setFont(QFont("Segoe UI", 10))
    # v48 installs the staged passive-plan renderer; its v47 base owns the
    # current fast/opacity-correct overlay.
    window = staged_release.previous.FixedInteractionOverlay()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
