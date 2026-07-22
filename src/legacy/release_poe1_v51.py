"""PoE 1 overlay with a tiny always-visible passive route preview."""

from __future__ import annotations

from pathlib import Path

from PyQt5.QtCore import QTimer

import main as legacy
import release_poe1_v48 as staged_release
import release_poe1_v50 as previous
from poe1_builds import clamp_level
from poe1_client_log_v2 import class_matches
from poe1_client_monitor_v3 import ClientLevelMonitor
from poe1_mini_tree_v9 import MiniPassiveRoute


from actpilot.overlay import MiniTreeOverlay_v51 as MiniTreeOverlay


def main():
    previous.editor_release.ManualBuildEditor = previous.ManualBuildEditor
    app = legacy.QApplication.instance()
    if app is None:
        return previous.main()
    window = MiniTreeOverlay()
    window.show()
    return window

