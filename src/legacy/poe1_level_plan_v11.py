"""Nearest connected ordinary-passive route with ascendancy strictly excluded."""

from __future__ import annotations

from poe1_level_plan import _is_tree_divider
from poe1_level_plan_v5 import quest_aware_passive_plan
from poe1_level_plan_v10 import nearest_connected_order


def ordinary_nearest_plan(stages, level, graph, positions, node_data):
    allowed = {
        str(node_id) for node_id in positions
        if not node_data.get(str(node_id), {}).get("ascendancyName")
    }
    filtered_stages = []
    previous = []
    for stage in stages:
        target = [node for node in stage.get("nodes", []) if str(node) in allowed]
        filtered = dict(stage)
        if _is_tree_divider(stage):
            filtered["nodes"] = target
            previous = target
        else:
            target_keys = {str(node) for node in target}
            base = [node for node in previous if str(node) in target_keys]
            additions = nearest_connected_order(base, target, graph, positions)
            filtered["nodes"] = base + additions
            previous = target
        filtered_stages.append(filtered)
    return quest_aware_passive_plan(
        filtered_stages, level, graph, kill_all_bandits=False
    )
