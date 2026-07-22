"""PoE 1 release with robust Russian/English Client.txt level synchronization."""

from __future__ import annotations

import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication

import main as legacy
import main_poe1_enhanced as enhanced
import release_poe1_v41 as previous
from poe1_client_log_v2 import class_matches
from poe1_client_monitor_v2 import ClientLevelMonitor
from poe1_builds import clamp_level


from actpilot.build_dialog import ReliableClientBuildDialog


from actpilot.overlay import ReliableClientOverlay


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setApplicationName(legacy.APP_NAME)
    app.setApplicationDisplayName(legacy.APP_NAME + " — PoE 1")
    legacy.ensure_cormorant_loaded()
    app.setFont(QFont("Segoe UI", 10))
    window = ReliableClientOverlay()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
