"""Render the passive snapshot active at the selected character level."""

from __future__ import annotations

from poe1_level_plan_v5 import passive_point_events
from poe1_manual_build_v4 import class_start_id, load_tree, normalize_passive_stages


def manual_passive_plan(build, level):
    state = (build or {}).get("manual_editor") or {}
    nodes = load_tree().get("nodes", {})
    start = class_start_id(nodes, state.get("class", "Witch"))
    stages = normalize_passive_stages(state)
    eligible = [stage for stage in stages if int(stage.get("level", 1)) <= int(level)]
    stage = eligible[-1] if eligible else stages[0]
    order = [str(node) for node in stage.get("allocation_order", [])]
    known = {str(node) for node in stage.get("passives", [])} | {
        str(node) for node in stage.get("masteries", {})
    }
    order = [node for node in order if node in known]
    for node in list(stage.get("passives", [])) + list(stage.get("masteries", {})):
        node = str(node)
        if node not in order:
            order.append(node)

    events = passive_point_events(kill_all_bandits=False)
    node_events = {
        node: events[index] for index, node in enumerate(order) if index < len(events)
    }
    completed_order = [
        node for node in order
        if node_events.get(node, {}).get("level", 10_000) <= int(level)
    ]
    completed_set = set(completed_order)
    upcoming = [node for node in order if node not in completed_set]
    effects = {
        str(node): effect for node, effect in stage.get("masteries", {}).items() if effect
    }
    mastery_raw = ",".join(f"{{{node},{effect}}}" for node, effect in effects.items())
    target = {
        "level": int(stage.get("level", 1)),
        "title": f"Manual tree from level {stage.get('level', 1)}",
        "nodes": [start] + order,
        "masteries": mastery_raw,
    }
    return {
        "target": target,
        "stage": stage,
        "planned": [start] + order,
        "completed": [start] + completed_order,
        "upcoming": upcoming,
        "node_levels": {node: event["level"] for node, event in node_events.items()},
        "node_markers": {node: event["marker"] for node, event in node_events.items()},
        "node_sources": {node: event["source"] for node, event in node_events.items()},
    }

