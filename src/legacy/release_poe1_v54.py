"""Transparent passive mini-route attached to the right of the overlay."""

from __future__ import annotations

from PyQt5.QtCore import QPoint, Qt
from PyQt5.QtWidgets import QApplication, QHBoxLayout, QWidget

import main as legacy
import release_poe1_v51 as mini_release
from poe1_mini_tree_v3 import MiniPassiveRoute
from release_poe1_v53 import MiniTreeOverlay as BaseMiniTreeOverlay


from actpilot.overlay import MiniTreeOverlay_v54 as MiniTreeOverlay
