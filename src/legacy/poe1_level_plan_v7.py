"""Book-only progression restricted to nodes visible in the normal passive tree."""

from __future__ import annotations

from poe1_level_plan_v5 import quest_aware_passive_plan


def visible_book_passive_plan(stages, level, graph, visible_nodes):
    allowed = {str(node) for node in visible_nodes}
    filtered_stages = []
    for stage in stages:
        filtered = dict(stage)
        filtered["nodes"] = [
            node for node in stage.get("nodes", []) if str(node) in allowed
        ]
        filtered_stages.append(filtered)
    return quest_aware_passive_plan(
        filtered_stages,
        level,
        graph,
        kill_all_bandits=False,
    )
