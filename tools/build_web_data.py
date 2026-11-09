"""Собирает данные для веб-интерфейса (web/data/*.json) из бандла приложения.

Запуск: py -3 tools/build_web_data.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src" / "actpilot"
WEB_DATA = ROOT / "web" / "data"

STEPS_FILE = SRC / "steps.json"
EXTRAS_FILE = SRC / "data" / "poe1" / "campaign_extras.json"
TREE_FILE = SRC / "data" / "poe1" / "skilltree.json"
GEMS_FILE = SRC / "data" / "poe1" / "gem_acquisition.json"

ACT_LABELS = [f"Акт {index}" for index in range(1, 11)]


def steps_payload() -> dict:
    raw = json.loads(STEPS_FILE.read_text(encoding="utf-8"))
    extras = {}
    try:
        extras = json.loads(EXTRAS_FILE.read_text(encoding="utf-8")).get("acts", {})
    except OSError:
        pass
    acts = []
    for index, (act, steps) in enumerate(raw.items()):
        items = []
        for step_index, step in enumerate(steps):
            text = step["text"] if isinstance(step, dict) else str(step)
            items.append({"id": f"{index}:{step_index}", "text": text})
        acts.append(
            {
                "name": ACT_LABELS[index] if index < len(ACT_LABELS) else act,
                "key": act,
                "steps": items,
                "extras": [item.get("text", "") for item in extras.get(act, []) if item.get("text")],
            }
        )
    return {"acts": acts}


def tree_payload() -> dict:
    data = json.loads(TREE_FILE.read_text(encoding="utf-8"))
    constants = data.get("constants", {})
    groups_raw = data.get("groups", {})
    groups = {}
    for key, group in groups_raw.items():
        if group.get("isProxy"):
            continue
        groups[key] = [round(float(group.get("x", 0)), 2), round(float(group.get("y", 0)), 2)]

    nodes = {}
    for node_id, node in data.get("nodes", {}).items():
        if node.get("isProxy") or node.get("isBlighted") or str(node.get("group")) not in groups:
            continue
        kind = 0
        if node.get("isNotable"):
            kind = 1
        elif node.get("isKeystone"):
            kind = 2
        elif node.get("isMastery"):
            kind = 3
        elif node.get("isJewelSocket"):
            kind = 4
        elif node.get("isMultipleChoice"):
            kind = 5
        entry = {
            "g": node.get("group"),
            "o": node.get("orbit", 0),
            "i": node.get("orbitIndex", 0),
            "k": kind,
            "out": [str(other) for other in node.get("out", [])],
        }
        name = (node.get("name") or "").strip()
        if name:
            entry["n"] = name
        if node.get("ascendancyName"):
            entry["asc"] = node["ascendancyName"]
        if "classStartIndex" in node:
            entry["cs"] = node["classStartIndex"]
        if kind in (1, 2, 3) and node.get("stats"):
            entry["s"] = node["stats"][:4]
        nodes[str(node_id)] = entry

    classes = [
        {"name": item.get("name"), "ascendancies": [a.get("id") for a in item.get("ascendancies", [])]}
        for item in data.get("classes", [])
    ]

    return {
        "min_x": data.get("min_x"),
        "max_x": data.get("max_x"),
        "min_y": data.get("min_y"),
        "max_y": data.get("max_y"),
        "orbit_radii": constants.get("orbitRadii", []),
        "per_orbit": constants.get("skillsPerOrbit", []),
        "groups": groups,
        "nodes": nodes,
        "classes": classes,
    }


def gems_payload() -> dict:
    """Только то, что нужно веб-плану: квесты с наградами/вендорами и имена камней."""
    data = json.loads(GEMS_FILE.read_text(encoding="utf-8"))
    gems = data.get("gems", {})
    known = set(gems)
    for kinds in (data.get("start_gems") or {}).values():
        known.update(value for value in kinds.values() if value)
    quests = []
    for quest in data.get("quests", []):
        offers = []
        for offer in quest.get("offers", []):
            offers.append(
                {
                    "npc": offer.get("npc", ""),
                    "rewards": offer.get("rewards", {}),
                    "vendor": offer.get("vendor", {}),
                }
            )
        quests.append({"act": quest.get("act"), "name": quest.get("name", ""), "offers": offers})
    names = {key: (record.get("name") or key) for key, record in gems.items()}
    return {
        "classes": data.get("classes", []),
        "start_gems": data.get("start_gems", {}),
        "quests": quests,
        "known": sorted(known),
        "names": names,
    }


def main() -> int:
    WEB_DATA.mkdir(parents=True, exist_ok=True)
    steps = steps_payload()
    tree = tree_payload()
    gems = gems_payload()

    (WEB_DATA / "steps.json").write_text(
        json.dumps(steps, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    (WEB_DATA / "tree.json").write_text(
        json.dumps(tree, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    (WEB_DATA / "gems.json").write_text(
        json.dumps(gems, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )

    steps_size = (WEB_DATA / "steps.json").stat().st_size
    tree_size = (WEB_DATA / "tree.json").stat().st_size
    gems_size = (WEB_DATA / "gems.json").stat().st_size
    print(f"steps.json: {steps_size / 1024:.0f} KB, {len(steps['acts'])} актов, "
          f"{sum(len(act['steps']) for act in steps['acts'])} шагов")
    print(f"tree.json: {tree_size / 1024:.0f} KB, {len(tree['nodes'])} нод, {len(tree['groups'])} групп")
    print(f"gems.json: {gems_size / 1024:.0f} KB, {len(gems['quests'])} квестов, "
          f"{len(gems['known'])} ключей камней")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
