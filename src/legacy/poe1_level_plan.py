"""Level-aware selection of PoB snapshots and inferred passive progression."""

from __future__ import annotations

import re

from poe1_builds import clamp_level
from poe1_progression import connected_addition_order


RANGE = re.compile(r"(?<!\d)(\d{1,3})\s*[-–—]\s*(\d{1,3})(?!\d)")


def range_bounds(stage):
    match = RANGE.search(stage.get("title", ""))
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def stage_at_level(stages, level):
    """Select the newest matching range, including shared range boundaries."""
    if not stages:
        return None
    level = clamp_level(level)
    ranged = []
    for index, stage in enumerate(stages):
        bounds = range_bounds(stage)
        if bounds and bounds[0] <= level <= bounds[1]:
            ranged.append((bounds[0], index, stage))
    if ranged:
        return max(ranged, key=lambda item: (item[0], item[1]))[2]
    eligible = [
        (clamp_level(stage.get("level", 1)), index, stage)
        for index, stage in enumerate(stages)
        if clamp_level(stage.get("level", 1)) <= level
    ]
    if eligible:
        return max(eligible, key=lambda item: (item[0], item[1]))[2]
    return min(
        enumerate(stages),
        key=lambda item: (clamp_level(item[1].get("level", 1)), item[0]),
    )[1]


def _is_tree_divider(stage):
    title = stage.get("title", "")
    return "----" in title or len(stage.get("nodes", [])) <= 2


def passive_plan(stages, level, graph):
    """Infer an ordered per-level state between coarse PoB tree snapshots."""
    level = clamp_level(level)
    indexed = list(enumerate(stages))
    real = [(index, stage) for index, stage in indexed if not _is_tree_divider(stage)]
    if not real:
        stage = stage_at_level(stages, level)
        nodes = list(stage.get("nodes", [])) if stage else []
        return {
            "current": stage,
            "target": stage,
            "planned": nodes,
            "completed": nodes,
            "upcoming": [],
        }

    eligible = [
        (clamp_level(stage.get("level", 1)), index, stage)
        for index, stage in real
        if clamp_level(stage.get("level", 1)) <= level
    ]
    current = max(eligible, key=lambda item: (item[0], item[1]))[2] if eligible else None
    current_level = clamp_level(current.get("level", 1)) if current else 1

    if current:
        later = [
            (clamp_level(stage.get("level", 1)), index, stage)
            for index, stage in real
            if clamp_level(stage.get("level", 1)) > current_level
        ]
    else:
        later = [
            (clamp_level(stage.get("level", 1)), index, stage)
            for index, stage in real
        ]
    target = min(later, key=lambda item: (item[0], item[1]))[2] if later else current

    if current:
        base = list(current.get("nodes", []))
    else:
        seed_candidates = [
            stage for _, stage in indexed
            if _is_tree_divider(stage) and stage.get("nodes")
        ]
        base = list(seed_candidates[0].get("nodes", [])) if seed_candidates else []

    if not target or target is current:
        return {
            "current": current,
            "target": target,
            "planned": base,
            "completed": base,
            "upcoming": [],
        }

    planned = list(target.get("nodes", []))
    order = connected_addition_order(base, planned, graph)
    target_level = clamp_level(target.get("level", current_level + 1))
    span = max(1, target_level - current_level)
    elapsed = max(0, min(span - 1, level - current_level))
    acquired_count = min(len(order), int(len(order) * elapsed / span))
    completed = list(base) + order[:acquired_count]
    return {
        "current": current,
        "target": target,
        "planned": planned,
        "completed": completed,
        "upcoming": order[acquired_count:],
    }
