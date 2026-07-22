"""Живые PoB level-планы v1,v3..v12, сведённые в один модуль (v2 в level_plans_v2)."""

from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET

from actpilot.builds import clamp_level, decode_pob_xml
from actpilot.progression import connected_addition_order


RANGE = re.compile(r"(?<!\d)(\d{1,3})\s*[-–—]\s*(\d{1,3})(?!\d)")


def range_bounds(stage):
    match = RANGE.search(stage.get("title", ""))
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def stage_at_level(stages, level):
    if not stages:
        return None
    level = clamp_level(level)
    ranged = []
    for index, stage in enumerate(stages):
        bounds = range_bounds(stage)
        if bounds and bounds[0] <= level <= bounds[1]:
            ranged.append((bounds[0], index, stage))
    if ranged:
        return max(ranged, key=lambda item: (item[0], item[1]))[2]
    eligible = [
        (clamp_level(stage.get("level", 1)), index, stage)
        for index, stage in enumerate(stages)
        if clamp_level(stage.get("level", 1)) <= level
    ]
    if eligible:
        return max(eligible, key=lambda item: (item[0], item[1]))[2]
    return min(
        enumerate(stages),
        key=lambda item: (clamp_level(item[1].get("level", 1)), item[0]),
    )[1]


def _is_tree_divider(stage):
    title = stage.get("title", "")
    return "----" in title or len(stage.get("nodes", [])) <= 2


def passive_plan(stages, level, graph):
    level = clamp_level(level)
    indexed = list(enumerate(stages))
    real = [(index, stage) for index, stage in indexed if not _is_tree_divider(stage)]
    if not real:
        stage = stage_at_level(stages, level)
        nodes = list(stage.get("nodes", [])) if stage else []
        return {
            "current": stage,
            "target": stage,
            "planned": nodes,
            "completed": nodes,
            "upcoming": [],
        }

    eligible = [
        (clamp_level(stage.get("level", 1)), index, stage)
        for index, stage in real
        if clamp_level(stage.get("level", 1)) <= level
    ]
    current = max(eligible, key=lambda item: (item[0], item[1]))[2] if eligible else None
    current_level = clamp_level(current.get("level", 1)) if current else 1

    if current:
        later = [
            (clamp_level(stage.get("level", 1)), index, stage)
            for index, stage in real
            if clamp_level(stage.get("level", 1)) > current_level
        ]
    else:
        later = [
            (clamp_level(stage.get("level", 1)), index, stage)
            for index, stage in real
        ]
    target = min(later, key=lambda item: (item[0], item[1]))[2] if later else current

    if current:
        base = list(current.get("nodes", []))
    else:
        seed_candidates = [
            stage for _, stage in indexed
            if _is_tree_divider(stage) and stage.get("nodes")
        ]
        base = list(seed_candidates[0].get("nodes", [])) if seed_candidates else []

    if not target or target is current:
        return {
            "current": current,
            "target": target,
            "planned": base,
            "completed": base,
            "upcoming": [],
        }

    planned = list(target.get("nodes", []))
    order = connected_addition_order(base, planned, graph)
    target_level = clamp_level(target.get("level", current_level + 1))
    span = max(1, target_level - current_level)
    elapsed = max(0, min(span - 1, level - current_level))
    acquired_count = min(len(order), int(len(order) * elapsed / span))
    completed = list(base) + order[:acquired_count]
    return {
        "current": current,
        "target": target,
        "planned": planned,
        "completed": completed,
        "upcoming": order[acquired_count:],
    }


def passive_plan_by_level(stages, level, graph):
    level = clamp_level(level)
    indexed = list(enumerate(stages))
    real = [(index, stage) for index, stage in indexed if not _is_tree_divider(stage)]
    if not real:
        return {
            "current": None, "target": None, "planned": [], "completed": [],
            "upcoming": [], "node_levels": {},
        }

    eligible = [
        (clamp_level(stage.get("level", 1)), index, stage)
        for index, stage in real
        if clamp_level(stage.get("level", 1)) <= level
    ]
    current = max(eligible, key=lambda item: (item[0], item[1]))[2] if eligible else None
    current_level = clamp_level(current.get("level", 1)) if current else 1
    later = [
        (clamp_level(stage.get("level", 1)), index, stage)
        for index, stage in real
        if clamp_level(stage.get("level", 1)) > current_level
    ]
    target = min(later, key=lambda item: (item[0], item[1]))[2] if later else current

    if current:
        base = list(current.get("nodes", []))
    else:
        seeds = [stage for _, stage in indexed if _is_tree_divider(stage) and stage.get("nodes")]
        base = list(seeds[0].get("nodes", [])) if seeds else []

    if not target or target is current:
        return {
            "current": current,
            "target": target,
            "planned": base,
            "completed": base,
            "upcoming": [],
            "node_levels": {},
        }

    planned = list(target.get("nodes", []))
    order = connected_addition_order(base, planned, graph)
    target_level = clamp_level(target.get("level", current_level + 1))
    span = max(1, target_level - current_level)
    node_levels = {}
    for index, node in enumerate(order):
        # PoB milestones often contain quest passive points, so several nodes may
        # legitimately share a character level. Every node still gets a level.
        offset = max(1, math.ceil((index + 1) * span / max(1, len(order))))
        node_levels[str(node)] = min(target_level, current_level + offset)

    completed_additions = [
        node for node in order if node_levels[str(node)] <= level
    ]
    upcoming = [node for node in order if node_levels[str(node)] > level]
    return {
        "current": current,
        "target": target,
        "planned": planned,
        "completed": list(base) + completed_additions,
        "upcoming": upcoming,
        "node_levels": node_levels,
    }


def strict_passive_plan(stages, level, graph):
    level = clamp_level(level)
    indexed = list(enumerate(stages))
    real = [stage for _, stage in indexed if not _is_tree_divider(stage)]
    seeds = [stage for _, stage in indexed if _is_tree_divider(stage) and stage.get("nodes")]
    previous = list(seeds[0].get("nodes", [])) if seeds else []
    cursor_level = 1
    segments = []

    for stage in real:
        target = list(stage.get("nodes", []))
        target_keys = {str(node) for node in target}
        base = [node for node in previous if str(node) in target_keys]
        additions = connected_addition_order(base, target, graph)
        assignments = {}
        for node in additions:
            cursor_level += 1
            assignments[str(node)] = cursor_level
        segments.append(
            {
                "target": stage,
                "planned": target,
                "base": base,
                "additions": additions,
                "node_levels": assignments,
            }
        )
        previous = target

    if not segments:
        return {
            "target": None, "planned": previous, "completed": previous,
            "upcoming": [], "node_levels": {},
        }

    active = None
    for segment in segments:
        if any(required > level for required in segment["node_levels"].values()):
            active = segment
            break
    if active is None:
        active = segments[-1]

    completed_additions = [
        node for node in active["additions"]
        if active["node_levels"].get(str(node), 1) <= level
    ]
    upcoming = [
        node for node in active["additions"]
        if active["node_levels"].get(str(node), 1) > level
    ]
    completed = list(active["base"]) + completed_additions
    if not upcoming:
        completed = list(active["planned"])
    return {
        "target": active["target"],
        "planned": active["planned"],
        "completed": completed,
        "upcoming": upcoming,
        "node_levels": active["node_levels"],
    }


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


def book_only_passive_plan(stages, level, graph):
    return quest_aware_passive_plan(
        stages, level, graph, kill_all_bandits=False
    )


def visible_book_passive_plan(stages, level, graph, visible_nodes):
    allowed = {str(node) for node in visible_nodes}
    filtered_stages = []
    for stage in stages:
        filtered = dict(stage)
        filtered["nodes"] = [
            node for node in stage.get("nodes", []) if str(node) in allowed
        ]
        filtered_stages.append(filtered)
    return quest_aware_passive_plan(
        filtered_stages,
        level,
        graph,
        kill_all_bandits=False,
    )


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


def corrected_semantic_order(previous, target, graph, node_data):
    allocated = {str(node) for node in previous}
    target_order = [str(node) for node in target]
    target_set = set(target_order)
    original_index = {node: index for index, node in enumerate(target_order)}
    remaining = [node for node in target_order if node not in allocated]
    ordered = []
    current = None

    def priority(node):
        data = node_data.get(node, {})
        if data.get("isKeystone"):
            kind = 0
        elif data.get("isNotable"):
            kind = 1
        elif data.get("isMastery"):
            kind = 2
        else:
            kind = 3
        degree = len(graph.get(node, set()) & target_set)
        return kind, -degree, original_index[node]

    while remaining:
        local = [
            node for node in remaining
            if current is not None and node in graph.get(current, set())
        ]
        frontier = [node for node in remaining if graph.get(node, set()) & allocated]
        candidates = local or frontier or remaining
        chosen = min(candidates, key=priority)
        remaining.remove(chosen)
        ordered.append(chosen)
        allocated.add(chosen)
        current = chosen
    return ordered


def corrected_semantic_plan(stages, level, graph, visible_nodes, node_data):
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
            additions = corrected_semantic_order(base, target, graph, node_data)
            filtered["nodes"] = base + additions
            previous = target
        filtered_stages.append(filtered)
    return quest_aware_passive_plan(
        filtered_stages, level, graph, kill_all_bandits=False
    )


def _xy(point):
    if hasattr(point, "x"):
        return float(point.x()), float(point.y())
    return float(point[0]), float(point[1])


def _distance(first, second, positions):
    if first not in positions or second not in positions:
        return float("inf")
    ax, ay = _xy(positions[first])
    bx, by = _xy(positions[second])
    return math.hypot(ax - bx, ay - by)


def nearest_connected_order(previous, target, graph, positions):
    allocated = {str(node) for node in previous}
    target_order = [str(node) for node in target]
    original_index = {node: index for index, node in enumerate(target_order)}
    remaining = [node for node in target_order if node not in allocated]
    ordered = []

    while remaining:
        frontier = []
        for node in remaining:
            parents = graph.get(node, set()) & allocated
            if parents:
                edge = min(_distance(node, parent, positions) for parent in parents)
                frontier.append((edge, original_index[node], node))
        if frontier:
            chosen = min(frontier)[2]
        else:
            # Malformed/intermediate PoB snapshots can be disconnected. Keep a
            # deterministic fallback, but never pretend there is a connection.
            chosen = min(remaining, key=lambda node: original_index[node])
        remaining.remove(chosen)
        ordered.append(chosen)
        allocated.add(chosen)
    return ordered


def nearest_connected_plan(stages, level, graph, positions, node_data=None):
    allowed = {str(node) for node in positions}
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
            additions = nearest_connected_order(base, target, graph, positions)
            filtered["nodes"] = base + additions
            previous = target
        filtered_stages.append(filtered)
    return quest_aware_passive_plan(
        filtered_stages, level, graph, kill_all_bandits=False
    )


def ordinary_nearest_plan(stages, level, graph, positions, node_data):
    allowed = {
        str(node_id) for node_id in positions
        if not node_data.get(str(node_id), {}).get("ascendancyName")
    }
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
            additions = nearest_connected_order(base, target, graph, positions)
            filtered["nodes"] = base + additions
            previous = target
        filtered_stages.append(filtered)
    return quest_aware_passive_plan(
        filtered_stages, level, graph, kill_all_bandits=False
    )


def mastery_separated_plan(stages, level, graph, positions, node_data):
    def ordinary(node):
        data = node_data.get(str(node), {})
        return str(node) in positions and not data.get("ascendancyName") and not data.get("isMastery")

    def mastery(node):
        data = node_data.get(str(node), {})
        return str(node) in positions and not data.get("ascendancyName") and data.get("isMastery")

    filtered_stages = []
    previous = []
    for stage in stages:
        raw = list(stage.get("nodes", []))
        regular_target = [node for node in raw if ordinary(node)]
        mastery_target = [node for node in raw if mastery(node)]
        target_keys = {str(node) for node in raw}
        base = [node for node in previous if str(node) in target_keys]
        base_regular = [node for node in base if ordinary(node)]
        base_mastery = [node for node in base if mastery(node)]
        if _is_tree_divider(stage):
            ordered = regular_target + mastery_target
        else:
            additions = nearest_connected_order(
                base_regular, regular_target, graph, positions,
            )
            old_mastery = {str(node) for node in base_mastery}
            new_mastery = [node for node in mastery_target if str(node) not in old_mastery]
            # A mastery still consumes a passive point, but it is scheduled only
            # after the ordinary path added by this PoB snapshot.
            ordered = base_regular + base_mastery + additions + new_mastery
        filtered = dict(stage)
        filtered["nodes"] = ordered
        filtered_stages.append(filtered)
        previous = ordered
    return quest_aware_passive_plan(
        filtered_stages, level, graph, kill_all_bandits=False,
    )
