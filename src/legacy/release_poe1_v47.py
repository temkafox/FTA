"""PoE 1 fast tree with fixed manual selection and reliable window opacity."""

from __future__ import annotations

import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication

import main as legacy
import release_poe1_v41 as editor_release
import release_poe1_v46 as previous
from poe1_manual_editor_v6 import ManualBuildEditor


from actpilot.build_dialog import FixedInteractionBuildDialog


class FixedInteractionOverlay(previous.FastTreeOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = FixedInteractionBuildDialog(self)
        else:
            self._build_dialog.reload()
        self._build_dialog.sync_window_opacity()
        self._build_dialog.show()
        self._build_dialog.raise_()
        self._build_dialog.activateWindow()

    def _settings(self):
        super()._settings()
        if self._build_dialog is not None:
            self._build_dialog.sync_window_opacity()


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setApplicationName(legacy.APP_NAME)
    app.setApplicationDisplayName(legacy.APP_NAME + " — PoE 1")
    legacy.ensure_cormorant_loaded()
    app.setFont(QFont("Segoe UI", 10))
    window = FixedInteractionOverlay()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
