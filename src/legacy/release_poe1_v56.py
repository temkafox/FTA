"""Dock a dynamically sized, tree-positioned passive preview."""

from __future__ import annotations

from PyQt5.QtCore import QPoint
from PyQt5.QtWidgets import QApplication

import release_poe1_v51 as mini_release
from poe1_mini_tree_v5 import MiniPassiveRoute
from release_poe1_v55 import MiniTreeOverlay as BaseMiniTreeOverlay


from actpilot.overlay import MiniTreeOverlay_v56 as MiniTreeOverlay

