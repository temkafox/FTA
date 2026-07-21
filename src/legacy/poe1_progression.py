"""Turn coarse leveling PoB tree ranges into stable per-level passive states."""

from __future__ import annotations

import json
import re
from pathlib import Path

from poe1_builds import clamp_level


RANGE = re.compile(r"(?<!\d)(\d{1,3})\s*[-–—]\s*(\d{1,3})(?!\d)")


def range_bounds(stage: dict):
    match = RANGE.search(stage.get("title", ""))
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def build_adjacency(tree_file: Path) -> dict[str, set[str]]:
    try:
        nodes = json.loads(tree_file.read_text(encoding="utf-8")).get("nodes", {})
    except (OSError, ValueError):
        return {}
    graph = {str(node_id): set() for node_id in nodes}
    for node_id, node in nodes.items():
        first = str(node_id)
        for other in node.get("out", []) + node.get("in", []):
            second = str(other)
            if second in graph:
                graph[first].add(second)
                graph[second].add(first)
    return graph


def connected_addition_order(previous, target, graph):
    previous_set = {str(node) for node in previous}
    target_order = [str(node) for node in target]
    remaining = [node for node in target_order if node not in previous_set]
    allocated = set(previous_set)
    ordered = []
    while remaining:
        chosen_index = next(
            (index for index, node in enumerate(remaining) if graph.get(node, set()) & allocated),
            0,
        )
        node = remaining.pop(chosen_index)
        ordered.append(node)
        allocated.add(node)
    return ordered


def nodes_at_level(stage, previous_nodes, level, graph):
    """Return visible target nodes and the nodes newly revealed at this level."""
    target = [str(node) for node in stage.get("nodes", [])]
    previous = [str(node) for node in previous_nodes]
    bounds = range_bounds(stage)
    if not bounds:
        return target, [node for node in target if node not in set(previous)]
    start, end = bounds
    level = clamp_level(level)
    additions = connected_addition_order(previous, target, graph)

    def count_for(value):
        if value < start:
            return 0
        if value >= end:
            return len(additions)
        progress = (value - start + 1) / max(1, end - start + 1)
        return max(1, min(len(additions), round(len(additions) * progress)))

    current_count = count_for(level)
    prior_count = count_for(level - 1)
    visible = previous + additions[:current_count]
    newly_added = additions[prior_count:current_count]
    return visible, newly_added
