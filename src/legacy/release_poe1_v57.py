"""Restore the calculated native-tree size after legacy panel setup."""

from __future__ import annotations

from release_poe1_v56 import MiniTreeOverlay as BaseMiniTreeOverlay


class MiniTreeOverlay(BaseMiniTreeOverlay):
    def __init__(self):
        super().__init__()
        self.mini_tree._build_tree_layout()
        self._resize_mini_panel()

