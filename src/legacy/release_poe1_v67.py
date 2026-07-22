"""Use real kind-correct fallback gem art in both PoE 1 windows."""

from __future__ import annotations

import release_poe1_v35 as full_gem_release
import release_poe1_v60 as mini_gem_release
from poe1_gem_widgets_v9 import FallbackPoedbGemChains
from poe1_mini_gems_v5 import MiniGemLinks
from release_poe1_v66 import CompleteMiniTreeOverlay as BaseOverlay


from actpilot.overlay import KindCorrectGemOverlay
