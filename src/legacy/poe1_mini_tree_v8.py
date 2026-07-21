"""Local passive neighbourhood for both manual and imported PoB builds."""

from __future__ import annotations

from PyQt5.QtCore import QPointF

from poe1_level_plan_v5 import quest_aware_passive_plan
from poe1_mini_tree_v7 import MiniPassiveRoute as BaseMiniPassiveRoute


class MiniPassiveRoute(BaseMiniPassiveRoute):
    _graph = None

    def _tree_graph(self):
        if self.__class__._graph is None:
            graph = {str(node_id): set() for node_id in self._nodes}
            for node_id, node in self._nodes.items():
                first = str(node_id)
                for value in node.get("out", []) + node.get("in", []):
                    second = str(value)
                    if second in graph:
                        graph[first].add(second)
                        graph[second].add(first)
            self.__class__._graph = graph
        return self.__class__._graph

    def set_build_level(self, build, level):
        if not build or build.get("format") == "actpilot-manual-v1":
            return super().set_build_level(build, level)
        plan = quest_aware_passive_plan(
            build.get("trees", []), level, self._tree_graph(), False,
        )
        if not plan.get("target"):
            self._visible_nodes = []
            self._completed = set()
            self._planned = set()
            self._immediate = set()
            self._edges = []
            self._positions = {}
            self._layout_positions = {}
            self.setVisible(False)
            self.update()
            return
        self._set_local_plan(plan)

    def _set_local_plan(self, plan):
        completed = [str(node) for node in plan.get("completed", [])]
        upcoming = [str(node) for node in plan.get("upcoming", [])]
        planned = [str(node) for node in plan.get("planned", [])]
        self._completed = set(completed)
        self._planned = set(planned)
        self._immediate = set(upcoming[:1])
        known_upcoming = [node for node in upcoming if node in self._nodes]
        known_completed = [node for node in completed if node in self._nodes]
        known_planned = [node for node in planned if node in self._nodes]
        self._focus_node = (
            known_upcoming[0] if known_upcoming
            else known_completed[-1] if known_completed
            else known_planned[0] if known_planned
            else None
        )
        if not self._focus_node:
            self._visible_nodes = []
            self.setVisible(False)
            self.update()
            return

        focus = self._world_position(self._focus_node)
        visible = []
        positions = {}
        for node_id, node in self._nodes.items():
            node_id = str(node_id)
            if node.get("ascendancyName") or node.get("isAscendancyStart"):
                continue
            point = self._world_position(node_id)
            dx = (point.x() - focus.x()) / self.WORLD_X
            dy = (point.y() - focus.y()) / self.WORLD_Y
            if dx * dx + dy * dy <= 1.0:
                visible.append(node_id)
                positions[node_id] = point

        self._visible_nodes = visible
        self._positions = positions
        visible_set = set(visible)
        edges = set()
        for first in visible:
            node = self._node(first)
            for value in node.get("out", []) + node.get("in", []):
                second = str(value)
                if second in visible_set and second != first:
                    edges.add(tuple(sorted((first, second))))
        self._edges = sorted(edges)

        usable_w = self.VIEW_W - 12.0
        usable_h = self.VIEW_H - 12.0
        scale = min(
            usable_w / (self.WORLD_X * 2.0),
            usable_h / (self.WORLD_Y * 2.0),
        )
        self._layout_positions = {
            node_id: QPointF(
                self.VIEW_W / 2.0 + (point.x() - focus.x()) * scale,
                self.VIEW_H / 2.0 + (point.y() - focus.y()) * scale,
            )
            for node_id, point in positions.items()
        }
        self.setFixedSize(self.VIEW_W, self.VIEW_H)
        self.setVisible(True)
        self.update()

