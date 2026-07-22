"""Focused leveling tree; гем-классы переехали в actpilot.gems.widgets."""

from __future__ import annotations

from collections import deque

from PyQt5.QtCore import QPointF

from actpilot.gems.widgets import (
    CompactGemChains,
    CompactGemIcon,
    GemDetailTooltip,
)
from poe1_tree_renderer_v6 import LevelingRouteTreeCanvas


class FocusedLevelingTreeCanvas(LevelingRouteTreeCanvas):
    def upcoming_nodes(self, limit=10):
        adjacency = {node_id: set() for node_id in self.selected}
        for first, second in self.edges:
            if first in adjacency and second in adjacency:
                adjacency[first].add(second)
                adjacency[second].add(first)
        queue = deque(self.next_nodes)
        result = set(self.next_nodes)
        while queue and len(result) < limit:
            node = queue.popleft()
            for other in adjacency.get(node, set()):
                if other in self.route_nodes and other not in result:
                    result.add(other)
                    queue.append(other)
                    if len(result) >= limit:
                        break
        for node in list(self.next_nodes):
            result.update(adjacency.get(node, set()) & self.completed_nodes)
        return result

    def fit_upcoming(self):
        focus = self.upcoming_nodes()
        points = [self.positions[node] for node in focus if node in self.positions]
        if not points:
            return self.fit_selected()
        min_x, max_x = min(point.x() for point in points), max(point.x() for point in points)
        min_y, max_y = min(point.y() for point in points), max(point.y() for point in points)
        self.center = QPointF((min_x + max_x) / 2, (min_y + max_y) / 2)
        width, height = max(900, max_x - min_x), max(900, max_y - min_y)
        self.scale = max(0.055, min(0.22, (self.width() - 100) / width, (self.height() - 100) / height))
        self.update()
