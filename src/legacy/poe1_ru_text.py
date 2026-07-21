"""Offline Russian descriptions while preserving English entity names."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path


FILE = Path(__file__).parent / "data" / "poe1" / "ru_descriptions.json"
try:
    DATA = json.loads(FILE.read_text(encoding="utf-8"))
except (OSError, ValueError):
    DATA = {"nodes": {}, "gems": {}}


EXACT_STATS = {
    "Regenerate 1 Life per second for each 1% Uncapped Fire Resistance":
        "Восстанавливает 1 здоровья в секунду за каждый 1% незаполненного сопротивления огню",
    "Minions have 15% reduced Life Recovery rate":
        "Скорость восстановления здоровья приспешников снижена на 15%",
    "Minions have 30% increased maximum Life":
        "Максимум здоровья приспешников увеличен на 30%",
    "Auras from your Skills have 10% increased Effect on you":
        "Эффект аур от ваших умений на вас увеличен на 10%",
}


def translate_stat_fallback(text):
    if text in EXACT_STATS:
        return EXACT_STATS[text]
    match = re.fullmatch(r"([+-]?\d+(?:\.\d+)?) to (Intelligence|Strength|Dexterity)", text or "")
    if match:
        attribute = {
            "Intelligence": "интеллекту",
            "Strength": "силе",
            "Dexterity": "ловкости",
        }[match.group(2)]
        return f"{match.group(1)} к {attribute}"
    replacements = (
        ("increased", "увеличение"), ("reduced", "снижение"),
        ("maximum Life", "максимума здоровья"), ("Life", "здоровья"),
        ("Fire Resistance", "сопротивления огню"),
        ("Cold Resistance", "сопротивления холоду"),
        ("Lightning Resistance", "сопротивления молнии"),
        ("Elemental Resistances", "сопротивлений стихиям"),
        ("Damage", "урона"), ("Attack Speed", "скорости атаки"),
        ("Cast Speed", "скорости сотворения чар"),
    )
    result = text or ""
    for english, russian in replacements:
        result = result.replace(english, russian)
    return result


def localized_node(node):
    result = copy.deepcopy(node)
    node_id = str(node.get("_id", ""))
    record = DATA.get("nodes", {}).get(node_id, {})
    if record.get("stats"):
        result["stats"] = record["stats"]
    else:
        result["stats"] = [translate_stat_fallback(line) for line in node.get("stats", [])]
    effects = []
    for effect in node.get("masteryEffects", []):
        localized = dict(effect)
        localized["stats"] = [translate_stat_fallback(line) for line in effect.get("stats", [])]
        effects.append(localized)
    result["masteryEffects"] = effects
    return result


def gem_description(name):
    return DATA.get("gems", {}).get((name or "").casefold())
