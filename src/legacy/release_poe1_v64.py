"""Support PoB mini previews and same-colour fallback gem artwork."""

from __future__ import annotations

import main as legacy
import release_poe1_v51 as mini_tree_release
import release_poe1_v60 as mini_gem_release
from poe1_mini_gems_v3 import MiniGemLinks
from poe1_mini_tree_v8 import MiniPassiveRoute
from release_poe1_v63 import FixedGemOverviewOverlay as BaseOverlay


class PobMiniPreviewOverlay(BaseOverlay):
    def _profile_signature(self):
        base = super()._profile_signature()
        build = self.active_profile().get("build") or {}
        trees = tuple(
            (
                int(stage.get("level", 1)),
                tuple(str(node) for node in stage.get("nodes", [])),
            )
            for stage in build.get("trees", [])
        )
        return base, build.get("format", ""), trees

    def _sync_mini_gem_visibility(self):
        if self._mini_gem_panel is None or self.mini_gems is None:
            return
        show = (
            self.isVisible()
            and self.game == legacy.GAME_POE1
            and bool(self.mini_gems._links)
            and not self._mini_hidden_by_user
            and not getattr(self, "_mini_suspended", False)
        )
        self._mini_gem_panel.setVisible(show)
        if show:
            self._position_mini_gem_panel()
            self._mini_gem_panel.raise_()

