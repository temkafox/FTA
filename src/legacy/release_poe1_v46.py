"""PoE 1 build window with one cached tree construction and one initial reload."""

from __future__ import annotations

import importlib
import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication

import main as legacy
import main_poe1_enhanced as enhanced
import release_poe1_v35 as polished
import release_poe1_v41 as zoom_release
import release_poe1_v43 as reliable
from poe1_client_monitor_v3 import ClientLevelMonitor, find_client_log
from poe1_tree_fast import CachedZoomSafeTreeCanvas, ConstructionTreePlaceholder


def _replace_legacy_tree_constructors():
    replacements = {
        "main_poe1_enhanced": ("PassiveTreeCanvas",),
        "release_poe1_v2": ("CleanPassiveTreeCanvas",),
        "release_poe1_v3": ("ConnectedPassiveTreeCanvas",),
        "release_poe1_v4": ("MasteryAwareTreeCanvas",),
        "release_poe1_v5": ("OrbitalPassiveTreeCanvas",),
        "release_poe1_v6": ("LevelingRouteTreeCanvas",),
        "release_poe1_v7": ("FocusedLevelingTreeCanvas",),
        "release_poe1_v8": ("ProgressionTreeCanvas",),
        "release_poe1_v11": ("LevelMappedTreeCanvas",),
        "release_poe1_v13": ("ImmediateFocusTreeCanvas",),
        "release_poe1_v15": ("QuestAwareTreeCanvas",),
        "release_poe1_v20": ("CleanPassiveTreeCanvas",),
        "release_poe1_v24": ("IntegratedAscendancyTreeCanvas",),
        "release_poe1_v25": ("NativeAscendancyTreeCanvas",),
        "release_poe1_v26": ("RestoredAscendancyTreeCanvas",),
        "release_poe1_v27": ("RussianDescriptionTreeCanvas",),
        "release_poe1_v32": ("SeparateMasteryTreeCanvas",),
        "release_poe1_v36": ("ExplicitProgressionTreeCanvas",),
    }
    for module_name, names in replacements.items():
        module = importlib.import_module(module_name)
        for name in names:
            setattr(module, name, ConstructionTreePlaceholder)
    zoom_release.ZoomSafeTreeCanvas = CachedZoomSafeTreeCanvas


_replace_legacy_tree_constructors()
enhanced.ClientLevelMonitor = ClientLevelMonitor
polished.find_client_log = find_client_log


class FastBuildDialog(reliable.ReliableClientBuildDialog):
    def __init__(self, overlay):
        self._fast_construction_complete = False
        super().__init__(overlay)
        self._fast_construction_complete = True
        # Every inherited constructor attempted to reload. They were deferred,
        # so populate the fully assembled window exactly once now.
        super().reload()

    def reload(self):
        if not self._fast_construction_complete:
            return
        return super().reload()

    def refresh_level(self):
        if not self._fast_construction_complete:
            return
        return super().refresh_level()

    def closeEvent(self, event):
        # Keep the parsed tree and widgets alive. Reopening is then immediate.
        self.hide()
        event.ignore()


class FastTreeOverlay(reliable.ReliableClientOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        created = self._build_dialog is None
        if created:
            self._build_dialog = FastBuildDialog(self)
        else:
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
    window = FastTreeOverlay()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
