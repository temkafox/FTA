"""PoE 1 release without granted non-gems or gem levels in tooltips."""

from __future__ import annotations

import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication

import main as legacy
import release_poe1_v20 as previous
from poe1_gem_widgets_v4 import CleanArtworkGemChains


class SocketedGemBuildDialog(previous.CleanArtworkBuildDialog):
    def __init__(self, overlay):
        super().__init__(overlay)
        old_gems = self.gem_links
        gem_layout = old_gems.parentWidget().layout()
        gem_index = gem_layout.indexOf(old_gems)
        gem_layout.removeWidget(old_gems)
        old_gems.deleteLater()
        self.gem_links = CleanArtworkGemChains()
        self.gem_links.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        gem_layout.insertWidget(gem_index, self.gem_links, 1)
        self.reload()


class SocketedGemOverlay(previous.CleanArtworkOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = SocketedGemBuildDialog(self)
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
    app.setApplicationDisplayName(legacy.APP_NAME + " — PoE 1 CLEAN")
    legacy.ensure_cormorant_loaded()
    app.setFont(QFont("Segoe UI", 10))
    window = SocketedGemOverlay()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
