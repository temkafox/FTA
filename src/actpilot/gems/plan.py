"""План получения камней билда: что брать наградой за квест, что покупать и у кого."""

from __future__ import annotations

import copy
import html
import re
from functools import lru_cache

from actpilot.data_cache import game_data
from actpilot.gems.data import (
    GRANTED_NON_GEMS, acquisition_html, badges_for, normalized_class, required_level,
)


ACQUISITION = game_data("gem_acquisition.json")

# Уровень персонажа к концу акта; 33/55/68 совпадают с LAB_LEVELS в build_model
ACT_END_LEVEL = {1: 12, 2: 22, 3: 33, 4: 40, 5: 45, 6: 50, 7: 55, 8: 60, 9: 64, 10: 68}
PURCHASE_LEAD = 10
FREE_KINDS = {"start", "chest", "reward"}


def known_keys(data: dict) -> set:
    keys = set(data.get("gems", {}))
    for kinds in data.get("start_gems", {}).values():
        keys.update(kinds.values())
    return keys


KNOWN_KEYS = known_keys(ACQUISITION)


def gem_key(name, support=None, known=None) -> str:
    """Ключ справочника: PoB пишет саппорт без суффикса, справочник хранит с суффиксом."""
    known = KNOWN_KEYS if known is None else known
    key = (name or "").strip().casefold()
    if key.endswith(" support"):
        candidates = [key, key[: -len(" support")]]
    elif support:
        candidates = [f"{key} support", key]
    else:
        candidates = [key, f"{key} support"]
    return next((candidate for candidate in candidates if candidate in known), key)


def required_gems(build: dict, known=None) -> list[dict]:
    """Камни билда в порядке первого появления; копий — максимум в одном наборе."""
    needed = {}
    stages = sorted((build or {}).get("gem_sets", []), key=lambda stage: int(stage.get("level", 1)))
    for stage in stages:
        stage_level = int(stage.get("level", 1))
        counts = {}
        for link in stage.get("links", []):
            for gem in link.get("gems", []):
                name = (gem.get("name") or "").strip()
                if not name or name.casefold() in GRANTED_NON_GEMS:
                    continue
                key = gem_key(name, gem.get("support"), known)
                counts[key] = counts.get(key, 0) + 1
                if key not in needed:
                    needed[key] = {
                        "key": key,
                        "name": name,
                        "support": bool(gem.get("support")),
                        "level": max(stage_level, required_level(name) or 1),
                        "count": 0,
                    }
        for key, count in counts.items():
            needed[key]["count"] = max(needed[key]["count"], count)
    return list(needed.values())


def _missing_reason(name: str, known: set) -> dict:
    base = name.rsplit(" of ", 1)[0] if " of " in name else ""
    if base and gem_key(base, known=known) in known:
        return {"reason": "divine_font", "base": base}
    return {"reason": "trade", "base": None}


def plan_gems(needed: list[dict], class_name: str, data: dict) -> dict:
    """Жадно по порядку кампании: награда — первый нужный камень, остальное — покупка."""
    class_name = normalized_class(class_name)
    known = known_keys(data)
    owned = {item["key"]: 0 for item in needed}
    actions = {item["key"]: [] for item in needed}

    starts = data.get("start_gems", {}).get(class_name, {})
    for kind in ("start", "chest"):
        key = starts.get(kind)
        if key in owned and not owned[key]:
            owned[key] = 1
            actions[key].append({"kind": kind, "act": 1, "count": 1})

    quests = data.get("quests", [])
    last_vendor = {}
    for index, quest in enumerate(quests):
        for offer in quest["offers"]:
            for key, info in offer["vendor"].items():
                if class_name in info["classes"]:
                    last_vendor[key] = index

    steps = []
    for index, quest in enumerate(quests):
        act = quest["act"]
        step = {"act": act, "quest": quest["name"], "rewards": [], "purchases": []}
        for offer in quest["offers"]:
            for item in needed:
                key = item["key"]
                if owned[key] or class_name not in offer["rewards"].get(key, ()):
                    continue
                owned[key] = 1
                entry = {"kind": "reward", "act": act, "quest": quest["name"], "npc": offer["npc"], "count": 1}
                actions[key].append(entry)
                step["rewards"].append({**entry, "key": key, "name": item["name"], "support": item["support"]})
                break
        for offer in quest["offers"]:
            for item in needed:
                key = item["key"]
                missing = item["count"] - owned[key]
                info = offer["vendor"].get(key)
                if missing <= 0 or not info or class_name not in info["classes"]:
                    continue
                deferred = ACT_END_LEVEL.get(act, ACT_END_LEVEL[10]) < item["level"] - PURCHASE_LEAD
                if deferred and last_vendor.get(key) != index:
                    continue
                owned[key] += missing
                entry = {
                    "kind": "buy", "act": act, "quest": quest["name"], "npc": info["npc"],
                    "count": missing, "needed_level": item["level"], "deferred": deferred,
                }
                actions[key].append(entry)
                step["purchases"].append({**entry, "key": key, "name": item["name"], "support": item["support"]})
        if step["rewards"] or step["purchases"]:
            steps.append(step)

    gems, unavailable = {}, []
    for item in needed:
        key = item["key"]
        missing = _missing_reason(item["name"], known) if owned[key] < item["count"] else None
        gems[key] = {
            "name": item["name"], "support": item["support"], "actions": actions[key], "missing": missing,
        }
        if missing:
            unavailable.append({"key": key, "name": item["name"], "support": item["support"], **missing})
    return {"class": class_name, "steps": steps, "gems": gems, "unavailable": unavailable}


def build_gem_plan(build: dict) -> dict | None:
    class_name = normalized_class((build or {}).get("class"))
    if class_name not in ACQUISITION.get("classes", []):
        return None
    needed = required_gems(build)
    if not needed:
        return None
    signature = tuple(
        (item["key"], item["name"], item["support"], item["level"], item["count"]) for item in needed
    )
    return _cached_plan(signature, class_name)


# Кешированный план общий для всех потребителей — его нельзя мутировать
@lru_cache(maxsize=8)
def _cached_plan(signature: tuple, class_name: str) -> dict:
    fields = ("key", "name", "support", "level", "count")
    return plan_gems([dict(zip(fields, row)) for row in signature], class_name, ACQUISITION)


def annotate_links(links: list, plan: dict | None) -> list:
    result = copy.deepcopy(links or [])
    if not plan:
        return result
    for link in result:
        for gem in link.get("gems", []):
            info = plan["gems"].get(gem_key(gem.get("name"), gem.get("support")))
            if info:
                gem["plan"] = info
    return result


def plan_badges(gem: dict, class_name: str) -> str:
    info = (gem or {}).get("plan")
    if not info:
        return badges_for(gem.get("name"), class_name, gem.get("support"))
    kinds = {action["kind"] for action in info["actions"]}
    return ("Q" if kinds & FREE_KINDS else "") + ("B" if "buy" in kinds else "")


def plan_lines(info: dict) -> list[str]:
    lines = []
    for action in info.get("actions", []):
        kind = action["kind"]
        if kind == "start":
            lines.append("Стартовый камень класса")
        elif kind == "chest":
            lines.append("Сундук на Twilight Strand · Акт 1")
        elif kind == "reward":
            lines.append(f"Награда за {action['quest']} ({action['npc']}) · Акт {action['act']}")
        else:
            text = f"Купить у {action['npc']} после {action['quest']} · Акт {action['act']}"
            if action["count"] > 1:
                text += f" · ×{action['count']}"
            if action["deferred"]:
                text += f" · нужен с ур. {action['needed_level']}"
            lines.append(text)
    missing = info.get("missing")
    if missing:
        prefix = "Остальное: " if lines else ""
        if missing["reason"] == "divine_font":
            lines.append(f"{prefix}Divine Font в Лабиринте (из {missing['base']}) или трейд")
        else:
            lines.append(f"{prefix}только дроп или трейд")
    return lines


def plan_acquisition_html(gem: dict, class_name: str) -> str:
    details = acquisition_html(gem.get("name"), class_name, gem.get("support"))
    info = (gem or {}).get("plan")
    if not info:
        return details
    plan = "<br>".join(html.escape(line) for line in plan_lines(info))
    return (
        "<span style='color:#f0d387'><b>План</b></span><br>"
        f"{plan}<br><br><span style='color:#8f96a3'>Все варианты</span><br>{details}"
    )


def act_for_level(level: int) -> int | None:
    for act, end_level in sorted(ACT_END_LEVEL.items()):
        if int(level) <= end_level:
            return act
    return None


def campaign_act(step_act: str, level: int) -> int | None:
    """Акт активного шага кампании («Act 3»), иначе — оценка по уровню персонажа."""
    match = re.search(r"\d+", step_act or "")
    if match and int(match.group()) in ACT_END_LEVEL:
        return int(match.group())
    return act_for_level(level)


def act_items(plan: dict | None, act: int | None) -> list[tuple[dict, str]]:
    """Камни акта для краткой строки: (камень с планом, буква действия); отложенные покупки — нет."""
    if not plan or act is None:
        return []
    items = []
    for step in plan["steps"]:
        if step["act"] != act:
            continue
        for entry, letter in [(entry, "Q") for entry in step["rewards"]] + [
            (entry, "B") for entry in step["purchases"] if not entry["deferred"]
        ]:
            info = plan["gems"][entry["key"]]
            gem = {"name": info["name"], "support": info["support"], "plan": info}
            items.append((gem, letter))
    return items
