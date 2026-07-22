"""PoE 1 release with real per-level passive progression and fixed gem ranges."""

from __future__ import annotations

import sys

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication

import main as legacy
import release_poe1_v7 as previous
from actpilot.data_cache import tree_graph
from poe1_level_plan import passive_plan, stage_at_level
from poe1_target_widgets import ROOT
from poe1_tree_fast import ConstructionTreePlaceholder as ProgressionTreeCanvas


TREE_GRAPH = tree_graph(ROOT / "skilltree.json")


from actpilot.build_dialog import ProgressionBuildDialog


from actpilot.overlay import ProgressionOverlay


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setApplicationName(legacy.APP_NAME)
    app.setApplicationDisplayName(legacy.APP_NAME + " — PoE 1")
    legacy.ensure_cormorant_loaded()
    app.setFont(QFont("Segoe UI", 10))
    window = ProgressionOverlay()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
