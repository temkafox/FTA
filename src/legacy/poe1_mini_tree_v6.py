"""Native-positioned previous, current, and next passive preview."""

from __future__ import annotations

from poe1_mini_tree_v5 import MiniPassiveRoute as BaseMiniPassiveRoute


class MiniPassiveRoute(BaseMiniPassiveRoute):
    def _pick_nodes(self, completed, upcoming):
        completed = [str(node) for node in completed if str(node) in self._nodes]
        upcoming = [str(node) for node in upcoming if str(node) in self._nodes]
        chosen = []
        # Exactly: previous allocated -> most recently allocated -> next target.
        chosen.extend(completed[-2:])
        if upcoming:
            chosen.append(upcoming[0])
        elif len(completed) >= 3:
            chosen = completed[-3:]
        return chosen[-3:]

