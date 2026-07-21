"""Show a tiny native passive-tree neighbourhood beside the overlay."""

from __future__ import annotations

import release_poe1_v51 as mini_release
from poe1_mini_tree_v7 import MiniPassiveRoute
from release_poe1_v57 import MiniTreeOverlay as BaseMiniTreeOverlay


mini_release.MiniPassiveRoute = MiniPassiveRoute


class MiniTreeOverlay(BaseMiniTreeOverlay):
    pass

