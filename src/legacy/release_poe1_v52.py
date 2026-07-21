"""PoE 1 mini-tree that retains the passive taken at the latest level."""

from __future__ import annotations

import release_poe1_v51 as previous
from poe1_mini_tree_v2 import MiniPassiveRoute


# MiniTreeOverlay resolves this constructor in release_poe1_v51 at runtime.
previous.MiniPassiveRoute = MiniPassiveRoute


class MiniTreeOverlay(previous.MiniTreeOverlay):
    pass

