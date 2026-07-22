"""Final PoE 1 target UI with per-level passive interpolation."""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication

import main as legacy
import main_poe1_target as target
from actpilot.data_cache import tree_graph
from poe1_progression import nodes_at_level
from poe1_target_widgets import leveling_stage


TREE_FILE = Path(__file__).parent / "data" / "poe1" / "skilltree.json"
TREE_GRAPH = tree_graph(TREE_FILE)


from actpilot.build_dialog import PerLevelBuildDialog


class PerLevelOverlay(target.TargetPoe1Overlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = PerLevelBuildDialog(self)
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
    window = PerLevelOverlay()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
