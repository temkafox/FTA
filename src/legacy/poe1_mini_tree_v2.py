"""Route preview that keeps the node allocated by the latest level visible."""

from __future__ import annotations

from poe1_mini_tree import MiniPassiveRoute as BaseMiniPassiveRoute


class MiniPassiveRoute(BaseMiniPassiveRoute):
    def _pick_nodes(self, completed, upcoming):
        completed = [str(node) for node in completed if str(node) in self._nodes]
        upcoming = [str(node) for node in upcoming if str(node) in self._nodes]
        if not upcoming:
            return super()._pick_nodes(completed, upcoming)

        next_node = upcoming[0]
        last_completed = completed[-1] if completed else None
        parent = next(
            (node for node in reversed(completed) if self._connected(node, next_node)),
            None,
        )
        chosen = []
        for node in (last_completed, parent, next_node):
            if node and node not in chosen:
                chosen.append(node)
        if len(chosen) < 3:
            future = next(
                (node for node in upcoming[1:] if self._connected(next_node, node)),
                None,
            )
            if future and future not in chosen:
                chosen.append(future)
        return chosen[:3]

