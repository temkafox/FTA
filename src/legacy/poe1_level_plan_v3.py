"""Assign every inferred passive-tree node to a character level."""

from __future__ import annotations

import math

from poe1_builds import clamp_level
from poe1_level_plan import _is_tree_divider
from poe1_progression import connected_addition_order


def passive_plan_by_level(stages, level, graph):
    level = clamp_level(level)
    indexed = list(enumerate(stages))
    real = [(index, stage) for index, stage in indexed if not _is_tree_divider(stage)]
    if not real:
        return {
            "current": None, "target": None, "planned": [], "completed": [],
            "upcoming": [], "node_levels": {},
        }

    eligible = [
        (clamp_level(stage.get("level", 1)), index, stage)
        for index, stage in real
        if clamp_level(stage.get("level", 1)) <= level
    ]
    current = max(eligible, key=lambda item: (item[0], item[1]))[2] if eligible else None
    current_level = clamp_level(current.get("level", 1)) if current else 1
    later = [
        (clamp_level(stage.get("level", 1)), index, stage)
        for index, stage in real
        if clamp_level(stage.get("level", 1)) > current_level
    ]
    target = min(later, key=lambda item: (item[0], item[1]))[2] if later else current

    if current:
        base = list(current.get("nodes", []))
    else:
        seeds = [stage for _, stage in indexed if _is_tree_divider(stage) and stage.get("nodes")]
        base = list(seeds[0].get("nodes", [])) if seeds else []

    if not target or target is current:
        return {
            "current": current,
            "target": target,
            "planned": base,
            "completed": base,
            "upcoming": [],
            "node_levels": {},
        }

    planned = list(target.get("nodes", []))
    order = connected_addition_order(base, planned, graph)
    target_level = clamp_level(target.get("level", current_level + 1))
    span = max(1, target_level - current_level)
    node_levels = {}
    for index, node in enumerate(order):
        # PoB milestones often contain quest passive points, so several nodes may
        # legitimately share a character level. Every node still gets a level.
        offset = max(1, math.ceil((index + 1) * span / max(1, len(order))))
        node_levels[str(node)] = min(target_level, current_level + offset)

    completed_additions = [
        node for node in order if node_levels[str(node)] <= level
    ]
    upcoming = [node for node in order if node_levels[str(node)] > level]
    return {
        "current": current,
        "target": target,
        "planned": planned,
        "completed": list(base) + completed_additions,
        "upcoming": upcoming,
        "node_levels": node_levels,
    }
