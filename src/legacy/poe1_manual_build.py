"""Pure-data model for ActPilot's manual PoE 1 passive and gem editor."""

from __future__ import annotations

import copy
import json
from pathlib import Path

from poe1_level_plan_v5 import passive_point_events


ROOT = Path(__file__).parent
TREE_FILE = ROOT / "data" / "poe1" / "skilltree.json"

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
    return json.loads(TREE_FILE.read_text(encoding="utf-8"))


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
