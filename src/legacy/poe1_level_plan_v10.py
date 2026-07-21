"""Strict connected-frontier ordering using the shortest available tree edge."""

from __future__ import annotations

import math

from poe1_level_plan import _is_tree_divider
from poe1_level_plan_v5 import quest_aware_passive_plan


def _xy(point):
    if hasattr(point, "x"):
        return float(point.x()), float(point.y())
    return float(point[0]), float(point[1])


def _distance(first, second, positions):
    if first not in positions or second not in positions:
        return float("inf")
    ax, ay = _xy(positions[first])
    bx, by = _xy(positions[second])
    return math.hypot(ax - bx, ay - by)


def nearest_connected_order(previous, target, graph, positions):
    allocated = {str(node) for node in previous}
    target_order = [str(node) for node in target]
    original_index = {node: index for index, node in enumerate(target_order)}
    remaining = [node for node in target_order if node not in allocated]
    ordered = []

    while remaining:
        frontier = []
        for node in remaining:
            parents = graph.get(node, set()) & allocated
            if parents:
                edge = min(_distance(node, parent, positions) for parent in parents)
                frontier.append((edge, original_index[node], node))
        if frontier:
            chosen = min(frontier)[2]
        else:
            # Malformed/intermediate PoB snapshots can be disconnected. Keep a
            # deterministic fallback, but never pretend there is a connection.
            chosen = min(remaining, key=lambda node: original_index[node])
        remaining.remove(chosen)
        ordered.append(chosen)
        allocated.add(chosen)
    return ordered


def nearest_connected_plan(stages, level, graph, positions, node_data=None):
    allowed = {str(node) for node in positions}
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
