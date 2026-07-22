"""Tightly dock the compact chronological mini-tree beside the overlay."""

from __future__ import annotations

from PyQt5.QtCore import QPoint
from PyQt5.QtWidgets import QApplication

import release_poe1_v51 as mini_release
from poe1_mini_tree_v4 import MiniPassiveRoute
from release_poe1_v54 import MiniTreeOverlay as BaseMiniTreeOverlay


from actpilot.overlay import MiniTreeOverlay_v55 as MiniTreeOverlay

