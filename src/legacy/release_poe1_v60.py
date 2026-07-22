"""Add a transparent current-level gem preview below the passive mini-map."""

from __future__ import annotations

from PyQt5.QtCore import QPoint, Qt
from PyQt5.QtWidgets import QHBoxLayout, QWidget

from actpilot.minipanels import MiniGemLinksV5 as MiniGemLinks
from release_poe1_v59 import MiniTreeOverlay as BaseMiniTreeOverlay


from actpilot.overlay import MiniTreeAndGemsOverlay
