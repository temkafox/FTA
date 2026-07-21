"""Manual build model with level-bound passive-tree snapshots."""

from __future__ import annotations

import copy

import poe1_manual_build_v3 as previous
from poe1_manual_build import ascendancy_start_id, class_start_id, load_tree


SNAPSHOT_KEYS = ("passives", "masteries", "ascendancy_nodes", "allocation_order")


def _snapshot_from_state(state, level=1):
    snapshot = {"level": max(1, min(100, int(level)))}
    for key in SNAPSHOT_KEYS:
        default = {} if key == "masteries" else []
        snapshot[key] = copy.deepcopy(state.get(key, default))
    return snapshot


def normalize_passive_stages(state):
    stages = copy.deepcopy(state.get("passive_stages") or [])
    if not stages:
        stages = [_snapshot_from_state(state, 1)]
    normalized = []
    seen = set()
    for stage in sorted(stages, key=lambda item: int(item.get("level", 1))):
        level = max(1, min(100, int(stage.get("level", 1))))
        if level in seen:
            continue
        seen.add(level)
        item = {"level": level}
        for key in SNAPSHOT_KEYS:
            default = {} if key == "masteries" else []
            item[key] = copy.deepcopy(stage.get(key, default))
        normalized.append(item)
    return normalized or [_snapshot_from_state(state, 1)]


def state_from_build(build, level=1):
    state = previous.state_from_build(build, level)
    state["passive_stages"] = normalize_passive_stages(state)
    return state


def build_from_state(state):
    state = copy.deepcopy(state)
    stages = normalize_passive_stages(state)
    state["passive_stages"] = stages

    # Keep the currently edited snapshot in the legacy fields so older code
    # can still open the build without losing data.
    active = stages[-1]
    for key in SNAPSHOT_KEYS:
        state[key] = copy.deepcopy(active[key])
    result = previous.build_from_state(state)

    nodes = load_tree().get("nodes", {})
    start = class_start_id(nodes, state.get("class", "Witch"))
    asc_name = state.get("ascendancy", "")
    asc_start = ascendancy_start_id(nodes, asc_name)
    trees = []
    for stage in stages:
        order = [str(node) for node in stage.get("allocation_order", [])]
        known = {str(node) for node in stage.get("passives", [])} | {
            str(node) for node in stage.get("masteries", {})
        }
        order = [node for node in order if node in known]
        for node in list(stage.get("passives", [])) + list(stage.get("masteries", {})):
            node = str(node)
            if node not in order:
                order.append(node)
        asc_nodes = [str(node) for node in stage.get("ascendancy_nodes", [])]
        effects = {
            str(node): effect
            for node, effect in stage.get("masteries", {}).items()
            if effect
        }
        mastery_raw = ",".join(f"{{{node},{effect}}}" for node, effect in effects.items())
        trees.append({
            "level": int(stage["level"]),
            "title": f"Manual tree from level {stage['level']}",
            "tree_version": "manual-stages-v1",
            "nodes": [start] + order + ([asc_start] if asc_start else []) + asc_nodes,
            "masteries": mastery_raw,
        })
    result["trees"] = trees
    result["manual_editor"] = copy.deepcopy(state)
    return result

