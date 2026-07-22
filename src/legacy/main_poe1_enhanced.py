"""Enhanced PoE 1 launcher with visual tree, gem links and Client.txt sync."""

from __future__ import annotations

import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication, QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

import main as legacy
import main_poe1 as base
from poe1_tree_fast import ConstructionTreePlaceholder as PassiveTreeCanvas
from poe1_builds import clamp_level, stage_for_level
from poe1_client_monitor_v3 import ClientLevelMonitor
from poe1_widgets import GemLinksView


from actpilot.build_dialog import EnhancedBuildProgressDialog


class EnhancedPoe1Overlay(base.Poe1Overlay):
    def _interactive_widgets(self):
        widgets = super()._interactive_widgets()
        if hasattr(self, "build_btn") and self.build_btn not in widgets:
            widgets.append(self.build_btn)
        return widgets

    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = EnhancedBuildProgressDialog(self)
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
    window = EnhancedPoe1Overlay()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
