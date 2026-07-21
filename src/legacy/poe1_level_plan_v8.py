"""Semantic branch-local ordering for inferred PoE 1 passive progression."""

from __future__ import annotations

from poe1_level_plan import _is_tree_divider
from poe1_level_plan_v5 import quest_aware_passive_plan


def semantic_addition_order(previous, target, graph, node_data):
    allocated = {str(node) for node in previous}
    target_order = [str(node) for node in target]
    target_set = set(target_order)
    original_index = {node: index for index, node in enumerate(target_order)}
    remaining = [node for node in target_order if node not in allocated]
    ordered = []
    current = None

    def node_priority(node):
        data = node_data.get(node, {})
        if data.get("isKeystone"):
            kind = 0
        elif data.get("isNotable"):
            kind = 1
        elif data.get("isMastery"):
            kind = 2
        else:
            kind = 3
        target_degree = len(graph.get(node, set()) & target_set)
        return kind, target_degree, original_index[node]

    while remaining:
        local = [
            node for node in remaining
            if current is not None and node in graph.get(current, set())
        ]
        frontier = [
            node for node in remaining if graph.get(node, set()) & allocated
        ]
        candidates = local or frontier or remaining
        chosen = min(candidates, key=node_priority)
        remaining.remove(chosen)
        ordered.append(chosen)
        allocated.add(chosen)
        current = chosen
    return ordered


def semantic_book_passive_plan(stages, level, graph, visible_nodes, node_data):
    allowed = {str(node) for node in visible_nodes}
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
            additions = semantic_addition_order(base, target, graph, node_data)
            filtered["nodes"] = base + additions
            previous = target
        filtered_stages.append(filtered)
    return quest_aware_passive_plan(
        filtered_stages, level, graph, kill_all_bandits=False
    )
