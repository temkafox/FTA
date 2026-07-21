"""Exact per-point progression for manually authored PoE 1 builds."""

from __future__ import annotations

from poe1_level_plan_v5 import passive_point_events
from poe1_manual_build_v3 import class_start_id, load_tree


def manual_passive_plan(build, level):
    state = (build or {}).get("manual_editor") or {}
    nodes = load_tree().get("nodes", {})
    start = class_start_id(nodes, state.get("class", "Witch"))
    order = [str(node) for node in state.get("allocation_order", [])]
    events = passive_point_events(kill_all_bandits=False)
    node_events = {
        node: events[index] for index, node in enumerate(order) if index < len(events)
    }
    completed_order = [
        node for node in order if node_events.get(node, {}).get("level", 10_000) <= int(level)
    ]
    upcoming = [node for node in order if node not in set(completed_order)]
    target = max(
        (build or {}).get("trees", []),
        key=lambda item: len(item.get("nodes", [])),
        default={"title": "Manual route", "nodes": [start], "masteries": ""},
    )
    return {
        "target": target,
        "planned": [start] + order,
        "completed": [start] + completed_order,
        "upcoming": upcoming,
        "node_levels": {node: event["level"] for node, event in node_events.items()},
        "node_markers": {node: event["marker"] for node, event in node_events.items()},
        "node_sources": {node: event["source"] for node, event in node_events.items()},
    }
