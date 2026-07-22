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


class CombinedOverlay(previous.RouteOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = CombinedBuildDialog(self)
            self._build_dialog.finished.connect(
                lambda _: setattr(self, "_build_dialog", None)
            )
        self._build_dialog.reload()
        self._build_dialog.show()
        self._build_dialog.raise_()
        self._build_dialog.activateWindow()


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
