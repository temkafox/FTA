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


class ClearGemEditorOverlay(previous.StableEditorOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = ClearGemEditorBuildDialog(self)
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
    window = ClearGemEditorOverlay()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
