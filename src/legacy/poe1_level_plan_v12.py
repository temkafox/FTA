"""Nearest route with mastery allocations ordered separately from tree edges."""

from __future__ import annotations

from poe1_level_plan import _is_tree_divider
from poe1_level_plan_v5 import quest_aware_passive_plan
from poe1_level_plan_v10 import nearest_connected_order


def mastery_separated_plan(stages, level, graph, positions, node_data):
    def ordinary(node):
        data = node_data.get(str(node), {})
        return str(node) in positions and not data.get("ascendancyName") and not data.get("isMastery")

    def mastery(node):
        data = node_data.get(str(node), {})
        return str(node) in positions and not data.get("ascendancyName") and data.get("isMastery")

    filtered_stages = []
    previous = []
    for stage in stages:
        raw = list(stage.get("nodes", []))
        regular_target = [node for node in raw if ordinary(node)]
        mastery_target = [node for node in raw if mastery(node)]
        target_keys = {str(node) for node in raw}
        base = [node for node in previous if str(node) in target_keys]
        base_regular = [node for node in base if ordinary(node)]
        base_mastery = [node for node in base if mastery(node)]
        if _is_tree_divider(stage):
            ordered = regular_target + mastery_target
        else:
            additions = nearest_connected_order(
                base_regular, regular_target, graph, positions,
            )
            old_mastery = {str(node) for node in base_mastery}
            new_mastery = [node for node in mastery_target if str(node) not in old_mastery]
            # A mastery still consumes a passive point, but it is scheduled only
            # after the ordinary path added by this PoB snapshot.
            ordered = base_regular + base_mastery + additions + new_mastery
        filtered = dict(stage)
        filtered["nodes"] = ordered
        filtered_stages.append(filtered)
        previous = ordered
    return quest_aware_passive_plan(
        filtered_stages, level, graph, kill_all_bandits=False,
    )
