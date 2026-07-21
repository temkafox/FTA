"""Use colour-accurate mini gem art and detailed acquisition tooltips."""

from __future__ import annotations

import release_poe1_v60 as mini_gem_release
from poe1_mini_gems_v4 import MiniGemLinks
from release_poe1_v64 import PobMiniPreviewOverlay as BaseOverlay


mini_gem_release.MiniGemLinks = MiniGemLinks


class DetailedMiniGemOverlay(BaseOverlay):
    pass

