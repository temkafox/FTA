"""PoE 1: separate mastery, fixed Russian header and Q/B gem acquisition."""

from __future__ import annotations

import sys

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication

import main as legacy
import release_poe1_v28 as previous
import release_poe1_v27 as fallback_renderer
from poe1_gem_progression import links_at_level
from poe1_gem_widgets_v7 import AcquisitionGemChains
from poe1_level_plan_v2 import stage_at_level
from poe1_level_plan_v12 import mastery_separated_plan
from poe1_tree_fast import ConstructionTreePlaceholder as SeparateMasteryTreeCanvas
from release_poe1_v8 import TREE_GRAPH


from actpilot.build_dialog import MasteryAndQuestBuildDialog


class MasteryAndQuestOverlay(previous.StrictNearestOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = MasteryAndQuestBuildDialog(self)
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
    window = MasteryAndQuestOverlay()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
