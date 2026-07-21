"""Level-mapped tree focused only on the immediately actionable node."""

from __future__ import annotations

from PyQt5.QtCore import QPointF

from poe1_tree_renderer_v8 import LevelMappedTreeCanvas


class ImmediateFocusTreeCanvas(LevelMappedTreeCanvas):
    def immediate_focus_nodes(self):
        if not self.upcoming_order:
            return set(self.completed_nodes)
        next_node = self.upcoming_order[0]
        focus = {next_node}
        for first, second in self.edges:
            if first == next_node and second in self.completed_nodes:
                focus.add(second)
            elif second == next_node and first in self.completed_nodes:
                focus.add(first)
        return focus

    def upcoming_nodes(self, limit=10):
        return self.immediate_focus_nodes()

    def fit_upcoming(self):
        focus = self.immediate_focus_nodes()
        points = [self.positions[node] for node in focus if node in self.positions]
        if not points:
            return self.fit_selected()
        min_x, max_x = min(point.x() for point in points), max(point.x() for point in points)
        min_y, max_y = min(point.y() for point in points), max(point.y() for point in points)
        self.center = QPointF((min_x + max_x) / 2, (min_y + max_y) / 2)
        width = max(650, max_x - min_x)
        height = max(650, max_y - min_y)
        self.scale = max(
            0.09,
            min(0.24, (self.width() - 90) / width, (self.height() - 90) / height),
        )
        self.update()
