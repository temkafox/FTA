"""Show the passive mini-route after the main overlay becomes visible."""

from __future__ import annotations

from release_poe1_v52 import MiniTreeOverlay as BaseMiniTreeOverlay


class MiniTreeOverlay(BaseMiniTreeOverlay):
    def showEvent(self, event):
        super().showEvent(event)
        self._refresh_mini_tree(force=True)

