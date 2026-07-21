"""Fix editor rollback and add the active gem range to the mini HUD."""

from __future__ import annotations

import release_poe1_v41 as editor_release
import release_poe1_v50 as editor_bridge
import release_poe1_v60 as mini_gem_release
from poe1_manual_editor_v11 import ManualBuildEditor
from poe1_mini_gems_v2 import MiniGemLinks
from release_poe1_v62 import GemOverviewOverlay as BaseOverlay


# release_poe1_v51 historically restores this bridge value every time the
# editor opens. Patch both references so opening can no longer roll back v11.
editor_bridge.ManualBuildEditor = ManualBuildEditor
editor_bridge.editor_release.ManualBuildEditor = ManualBuildEditor
editor_release.ManualBuildEditor = ManualBuildEditor
mini_gem_release.MiniGemLinks = MiniGemLinks


class FixedGemOverviewOverlay(BaseOverlay):
    def _open_build_progress(self):
        editor_bridge.ManualBuildEditor = ManualBuildEditor
        editor_bridge.editor_release.ManualBuildEditor = ManualBuildEditor
        editor_release.ManualBuildEditor = ManualBuildEditor
        super()._open_build_progress()

