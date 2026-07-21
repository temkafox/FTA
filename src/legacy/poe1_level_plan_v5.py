"""Approximate PoE 1 passive budget including campaign quest rewards."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from poe1_builds import clamp_level, decode_pob_xml
from poe1_level_plan import _is_tree_divider
from poe1_progression import connected_addition_order


# Approximate character levels at which a normal campaign runner claims books.
# The final field is the number of passive points granted by the event.
QUEST_REWARDS = (
    (5, "Обитатель глубин", 1),
    (10, "Обманутый моряк", 1),
    (19, "Через священную землю", 1),
    (20, "Путь вперёд", 1),
    (27, "Секреты Виктарио", 1),
    (32, "Питомцы Пайети", 1),
    (38, "Неукротимый дух", 1),
    (44, "На службе науки", 1),
    (46, "Муки Китавы", 1),
    (48, "Отец войны", 1),
    (50, "Хозяйка кукол", 1),
    (52, "Расколотый", 1),
    (54, "Мастер миллиона лиц", 1),
    (56, "Королева отчаяния", 1),
    (58, "Звезда Кишары", 1),
    (60, "Любовь мертва", 1),
    (61, "Отражение ужаса", 1),
    (62, "Легион самоцветов", 1),
    (64, "Королева песков", 1),
    (65, "Правитель Высоких врат", 1),
    (67, "Месть Виленты", 1),
    (68, "Конец голоду", 2),
)


def pob_kills_all_bandits(build):
    source = (build or {}).get("source_code", "")
    if not source:
        return True
    try:
        root = ET.fromstring(decode_pob_xml(source))
        value = (root.find("Build").get("bandit", "None") or "None").casefold()
    except (ValueError, ET.ParseError, AttributeError):
        return True
    return value in {"none", "eramir", "killall", "kill all"}


def passive_point_events(kill_all_bandits=True, max_level=140):
    events = []
    order = 0
    for level in range(2, max_level + 1):
        events.append(
            {
                "level": level,
                "marker": str(level),
                "source": f"уровень персонажа {level}",
                "kind": "level",
                "order": order,
            }
        )
        order += 1
    for level, name, amount in QUEST_REWARDS:
        for point_index in range(amount):
            suffix = str(point_index + 1) if amount > 1 else ""
            events.append(
                {
                    "level": level,
                    "marker": f"{level}К{suffix}",
                    "source": f"квест «{name}»" + (f", очко {point_index + 1}" if amount > 1 else ""),
                    "kind": "quest",
                    "order": order,
                }
            )
            order += 1
    if kill_all_bandits:
        events.append(
            {
                "level": 20,
                "marker": "20Б",
                "source": "Эрамир: убиты все бандиты",
                "kind": "bandit",
                "order": order,
            }
        )
    priority = {"level": 0, "quest": 1, "bandit": 2}
    events.sort(key=lambda item: (item["level"], priority[item["kind"]], item["order"]))
    return events


def quest_aware_passive_plan(stages, level, graph, kill_all_bandits=True):
    level = clamp_level(level)
    indexed = list(enumerate(stages))
    real = [stage for _, stage in indexed if not _is_tree_divider(stage)]
    seeds = [stage for _, stage in indexed if _is_tree_divider(stage) and stage.get("nodes")]
    previous = list(seeds[0].get("nodes", [])) if seeds else []
    events = passive_point_events(kill_all_bandits)
    event_index = 0
    segments = []

    for stage in real:
        target = list(stage.get("nodes", []))
        target_keys = {str(node) for node in target}
        base = [node for node in previous if str(node) in target_keys]
        additions = connected_addition_order(base, target, graph)
        node_events = {}
        for node in additions:
            if event_index >= len(events):
                break
            node_events[str(node)] = events[event_index]
            event_index += 1
        segments.append(
            {
                "target": stage,
                "planned": target,
                "base": base,
                "additions": additions,
                "node_events": node_events,
            }
        )
        previous = target

    if not segments:
        return {
            "target": None, "planned": previous, "completed": previous,
            "upcoming": [], "node_levels": {}, "node_markers": {},
            "node_sources": {},
        }

    def is_future(segment, node):
        event = segment["node_events"].get(str(node))
        return event is not None and event["level"] > level

    active = next(
        (segment for segment in segments if any(is_future(segment, node) for node in segment["additions"])),
        segments[-1],
    )
    completed_additions = []
    upcoming = []
    for node in active["additions"]:
        event = active["node_events"].get(str(node))
        if event is None or event["level"] <= level:
            completed_additions.append(node)
        else:
            upcoming.append(node)
    completed = list(active["base"]) + completed_additions
    if not upcoming:
        completed = list(active["planned"])
    node_levels = {
        node: event["level"] for node, event in active["node_events"].items()
    }
    node_markers = {
        node: event["marker"] for node, event in active["node_events"].items()
    }
    node_sources = {
        node: event["source"] for node, event in active["node_events"].items()
    }
    return {
        "target": active["target"],
        "planned": active["planned"],
        "completed": completed,
        "upcoming": upcoming,
        "node_levels": node_levels,
        "node_markers": node_markers,
        "node_sources": node_sources,
    }
