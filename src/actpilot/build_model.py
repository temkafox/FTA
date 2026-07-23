"""Модели данных ручного билда: линии poe1_manual_build (v1..v4) и poe1_manual_plan_v2."""

from __future__ import annotations

import copy

from actpilot.data_cache import game_data
from actpilot.level_plans import passive_point_events


CLASS_START_INDEX = {
    "Scion": 0,
    "Marauder": 1,
    "Ranger": 2,
    "Witch": 3,
    "Duelist": 4,
    "Templar": 5,
    "Shadow": 6,
}

ASCENDANCIES = {
    "Scion": ["Ascendant"],
    "Marauder": ["Juggernaut", "Berserker", "Chieftain"],
    "Ranger": ["Deadeye", "Pathfinder", "Warden", "Raider"],
    "Witch": ["Necromancer", "Occultist", "Elementalist"],
    "Duelist": ["Slayer", "Gladiator", "Champion"],
    "Templar": ["Inquisitor", "Hierophant", "Guardian"],
    "Shadow": ["Assassin", "Saboteur", "Trickster"],
}

LAB_LEVELS = (33, 55, 68, 75)


def load_tree():
    # Общий кеш data_cache: skilltree.json (6.5 МБ) парсится один раз на процесс.
    # Все вызыватели (build_model, editor, minipanels) читают дерево только на чтение.
    return game_data("skilltree.json")


def class_start_id(nodes, class_name):
    wanted = CLASS_START_INDEX.get(class_name, CLASS_START_INDEX["Witch"])
    return next(
        (str(node_id) for node_id, node in nodes.items() if node.get("classStartIndex") == wanted),
        "54447",
    )


def ascendancy_start_id(nodes, ascendancy):
    return next(
        (
            str(node_id) for node_id, node in nodes.items()
            if node.get("ascendancyName") == ascendancy and node.get("isAscendancyStart")
        ),
        None,
    )


def passive_budget(level):
    return sum(
        1 for event in passive_point_events(kill_all_bandits=False)
        if event["level"] <= max(1, min(100, int(level)))
    )


def ascendancy_budget(level):
    level = max(1, min(100, int(level)))
    return 2 * sum(1 for lab_level in LAB_LEVELS if lab_level <= level)


def _richest_tree(build):
    trees = (build or {}).get("trees", [])
    return max(trees, key=lambda item: len(item.get("nodes", [])), default={})


def state_from_build(build, level=1):
    manual = copy.deepcopy((build or {}).get("manual_editor") or {})
    if manual:
        manual.setdefault("gem_stages", copy.deepcopy((build or {}).get("gem_sets", [])))
        return manual

    tree = load_tree()
    nodes = tree.get("nodes", {})
    class_name = (build or {}).get("class") or "Witch"
    if class_name not in CLASS_START_INDEX:
        class_name = "Witch"
    ascendancy = (build or {}).get("ascendancy") or ASCENDANCIES[class_name][0]
    target = [str(node) for node in _richest_tree(build).get("nodes", [])]
    start = class_start_id(nodes, class_name)
    ordinary = [
        node for node in target
        if node in nodes and not nodes[node].get("ascendancyName") and not nodes[node].get("isMastery")
    ]
    if start in ordinary:
        ordinary.remove(start)
    masteries = [node for node in target if nodes.get(node, {}).get("isMastery")]
    asc_start = ascendancy_start_id(nodes, ascendancy)
    ascendancy_nodes = [
        node for node in target
        if nodes.get(node, {}).get("ascendancyName") == ascendancy and node != asc_start
    ]
    return {
        "class": class_name,
        "ascendancy": ascendancy,
        "passives": ordinary,
        "masteries": {node: None for node in masteries},
        "ascendancy_nodes": ascendancy_nodes,
        "gem_stages": copy.deepcopy((build or {}).get("gem_sets", [])),
        "level": int(level),
    }


def build_from_state(state):
    tree = load_tree()
    nodes = tree.get("nodes", {})
    class_name = state.get("class") or "Witch"
    ascendancy = state.get("ascendancy") or ASCENDANCIES[class_name][0]
    start = class_start_id(nodes, class_name)
    asc_start = ascendancy_start_id(nodes, ascendancy)
    regular = [start] + [str(node) for node in state.get("passives", [])]
    regular += [str(node) for node in state.get("masteries", {})]
    ascendancy_nodes = [str(node) for node in state.get("ascendancy_nodes", [])]
    full = regular + ([asc_start] if asc_start else []) + ascendancy_nodes
    mastery_effects = {
        str(node): effect for node, effect in state.get("masteries", {}).items() if effect
    }
    mastery_raw = ",".join(f"{node}={effect}" for node, effect in mastery_effects.items())

    trees = [{
        "level": 1,
        "title": "---- Manual class start ----",
        "tree_version": "manual",
        "nodes": [start],
        "masteries": "",
    }]
    for lab_index, lab_level in enumerate(LAB_LEVELS, 1):
        asc_count = min(len(ascendancy_nodes), lab_index * 2)
        snapshot = regular + ([asc_start] if asc_start else []) + ascendancy_nodes[:asc_count]
        trees.append({
            "level": lab_level,
            "title": f"Manual route · Lab {lab_index}",
            "tree_version": "manual",
            "nodes": snapshot,
            "masteries": mastery_raw,
        })
    trees.append({
        "level": 100,
        "title": "Manual route · Target",
        "tree_version": "manual",
        "nodes": full,
        "masteries": mastery_raw,
    })

    stored = copy.deepcopy(state)
    stored["level"] = max(1, min(100, int(state.get("level", 1))))
    gem_stages = sorted(
        copy.deepcopy(state.get("gem_stages", [])),
        key=lambda item: int(item.get("level", 1)),
    )
    return {
        "format": "actpilot-manual-v1",
        "name": f"Manual {class_name} {ascendancy}",
        "class": class_name,
        "ascendancy": ascendancy,
        "character_level": stored["level"],
        "trees": trees,
        "gem_sets": gem_stages,
        "source_code": "",
        "manual_editor": stored,
    }


state_from_build_v1 = state_from_build
build_from_state_v1 = build_from_state


def build_from_state(state):
    result = build_from_state_v1(state)
    effects = {
        str(node): effect for node, effect in state.get("masteries", {}).items() if effect
    }
    raw = ",".join(f"{{{node},{effect}}}" for node, effect in effects.items())
    for tree in result.get("trees", []):
        if len(tree.get("nodes", [])) > 2:
            tree["masteries"] = raw
    return result


build_from_state_v2 = build_from_state


def state_from_build(build, level=1):
    state = state_from_build_v1(build, level)
    if not state.get("allocation_order"):
        state["allocation_order"] = (
            [str(node) for node in state.get("passives", [])]
            + [str(node) for node in state.get("masteries", {})]
        )
    return state


def build_from_state(state):
    state = copy.deepcopy(state)
    order = [str(node) for node in state.get("allocation_order", [])]
    known = {str(node) for node in state.get("passives", [])} | {
        str(node) for node in state.get("masteries", {})
    }
    order = [node for node in order if node in known]
    for node in list(state.get("passives", [])) + list(state.get("masteries", {})):
        node = str(node)
        if node not in order:
            order.append(node)
    state["allocation_order"] = order
    result = build_from_state_v2(state)

    nodes = load_tree().get("nodes", {})
    start = class_start_id(nodes, state.get("class", "Witch"))
    regular = [start] + order
    for tree in result.get("trees", []):
        ascendancy = [
            str(node) for node in tree.get("nodes", [])
            if nodes.get(str(node), {}).get("ascendancyName")
        ]
        if len(tree.get("nodes", [])) > 2:
            tree["nodes"] = regular + ascendancy
    result["manual_editor"] = copy.deepcopy(state)
    return result


state_from_build_v3 = state_from_build
build_from_state_v3 = build_from_state


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
    state = state_from_build_v3(build, level)
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
    result = build_from_state_v3(state)

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


state_from_build_v4 = state_from_build
build_from_state_v4 = build_from_state


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
