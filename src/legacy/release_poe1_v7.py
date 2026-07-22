"""PoE 1 release with compact gem links and a focused tree in one view."""

from __future__ import annotations

import sys

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

import main as legacy
import main_poe1 as base
import release_poe1_v6 as previous
from poe1_combined_widgets import CompactGemChains
from poe1_tree_fast import ConstructionTreePlaceholder as FocusedLevelingTreeCanvas
from poe1_target_widgets import leveling_stage


from actpilot.build_dialog import CombinedBuildDialog


from actpilot.overlay import CombinedOverlay


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setApplicationName(legacy.APP_NAME)
    app.setApplicationDisplayName(legacy.APP_NAME + " — PoE 1")
    legacy.ensure_cormorant_loaded()
    app.setFont(QFont("Segoe UI", 10))
    window = CombinedOverlay()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
