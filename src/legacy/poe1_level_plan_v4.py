"""Strict passive progression: one inferred passive node per character level."""

from __future__ import annotations

from poe1_builds import clamp_level
from poe1_level_plan import _is_tree_divider
from poe1_progression import connected_addition_order


def strict_passive_plan(stages, level, graph):
    level = clamp_level(level)
    indexed = list(enumerate(stages))
    real = [stage for _, stage in indexed if not _is_tree_divider(stage)]
    seeds = [stage for _, stage in indexed if _is_tree_divider(stage) and stage.get("nodes")]
    previous = list(seeds[0].get("nodes", [])) if seeds else []
    cursor_level = 1
    segments = []

    for stage in real:
        target = list(stage.get("nodes", []))
        target_keys = {str(node) for node in target}
        base = [node for node in previous if str(node) in target_keys]
        additions = connected_addition_order(base, target, graph)
        assignments = {}
        for node in additions:
            cursor_level += 1
            assignments[str(node)] = cursor_level
        segments.append(
            {
                "target": stage,
                "planned": target,
                "base": base,
                "additions": additions,
                "node_levels": assignments,
            }
        )
        previous = target

    if not segments:
        return {
            "target": None, "planned": previous, "completed": previous,
            "upcoming": [], "node_levels": {},
        }

    active = None
    for segment in segments:
        if any(required > level for required in segment["node_levels"].values()):
            active = segment
            break
    if active is None:
        active = segments[-1]

    completed_additions = [
        node for node in active["additions"]
        if active["node_levels"].get(str(node), 1) <= level
    ]
    upcoming = [
        node for node in active["additions"]
        if active["node_levels"].get(str(node), 1) > level
    ]
    completed = list(active["base"]) + completed_additions
    if not upcoming:
        completed = list(active["planned"])
    return {
        "target": active["target"],
        "planned": active["planned"],
        "completed": completed,
        "upcoming": upcoming,
        "node_levels": active["node_levels"],
    }
