"""Build a separate PoE 1 ascendancy route from imported PoB tree stages."""

from __future__ import annotations

import re


def _is_ascendancy(node, name):
    return bool(node) and node.get("ascendancyName") == name


def _lab_name(title):
    text = re.sub(r"\^[0-9]+", "", title or "").strip(" -")
    text = re.sub(r"(?i)^level\s*\d+\s*[-–:]?\s*", "", text).strip()
    return text or "Лабиринт"


def ascendancy_plan(trees, node_data, ascendancy_name, character_level):
    stages = sorted(trees or [], key=lambda item: (int(item.get("level", 1)), item.get("title", "")))
    snapshots = []
    first_seen = {}
    for stage in stages:
        ids = []
        for raw_id in stage.get("nodes", []):
            node_id = str(raw_id)
            node = node_data.get(node_id, {})
            if _is_ascendancy(node, ascendancy_name):
                ids.append(node_id)
                if not node.get("isAscendancyStart") and node_id not in first_seen:
                    first_seen[node_id] = {
                        "level": int(stage.get("level", 1)),
                        "lab": _lab_name(stage.get("title", "")),
                    }
        if ids:
            snapshots.append((len(ids), int(stage.get("level", 1)), ids))

    if not snapshots:
        return {"name": ascendancy_name or "Ассенданси", "nodes": [], "edges": [], "completed": [], "next": []}

    # PoB leveling exports sometimes contain later separator stages with only
    # the ascendancy start. The richest/latest snapshot is the actual target.
    _, _, target_ids = max(snapshots, key=lambda item: (item[0], item[1]))
    target = set(target_ids)
    start = next((node_id for node_id in target_ids if node_data.get(node_id, {}).get("isAscendancyStart")), None)
    route = [node_id for node_id in target_ids if node_id != start]
    route.sort(key=lambda node_id: (
        first_seen.get(node_id, {}).get("level", 10_000),
        0 if not node_data.get(node_id, {}).get("isNotable") else 1,
        node_data.get(node_id, {}).get("name", ""),
    ))
    ordered = ([start] if start else []) + route

    edges = []
    seen = set()
    for node_id in ordered:
        for other in node_data.get(node_id, {}).get("out", []):
            other = str(other)
            if other not in target:
                continue
            edge = tuple(sorted((node_id, other)))
            if edge not in seen:
                seen.add(edge)
                edges.append(edge)

    completed = [
        node_id for node_id in route
        if first_seen.get(node_id, {}).get("level", 10_000) <= int(character_level)
    ]
    future_levels = sorted({
        first_seen[node_id]["level"] for node_id in route
        if first_seen.get(node_id, {}).get("level", 10_000) > int(character_level)
    })
    next_level = future_levels[0] if future_levels else None
    next_nodes = [
        node_id for node_id in route
        if next_level is not None and first_seen[node_id]["level"] == next_level
    ]
    milestones = [
        {
            "node": node_id,
            "level": first_seen.get(node_id, {}).get("level"),
            "lab": first_seen.get(node_id, {}).get("lab", "Лабиринт"),
        }
        for node_id in route
    ]
    return {
        "name": ascendancy_name or "Ассенданси",
        "nodes": ordered,
        "edges": edges,
        "completed": completed,
        "next": next_nodes,
        "milestones": milestones,
        "next_lab": first_seen.get(next_nodes[0], {}).get("lab") if next_nodes else None,
    }
