"""Read class-aware PoE 1 gem acquisition data offline."""

from __future__ import annotations

import json
from pathlib import Path


FILE = Path(__file__).parent / "data" / "poe1" / "gem_acquisition.json"
try:
    DATA = json.loads(FILE.read_text(encoding="utf-8")).get("gems", {})
except (OSError, ValueError):
    DATA = {}


CLASS_ALIASES = {
    "witch": "Witch", "shadow": "Shadow", "ranger": "Ranger",
    "duelist": "Duelist", "marauder": "Marauder",
    "templar": "Templar", "scion": "Scion",
}


def normalized_class(value):
    return CLASS_ALIASES.get((value or "").strip().casefold(), (value or "").strip())


def acquisition_for(gem_name, class_name):
    record = DATA.get((gem_name or "").casefold(), {})
    ways = record.get("classes", {}).get(normalized_class(class_name), {})
    return {
        "quest": list(ways.get("quest", [])),
        "vendor": list(ways.get("vendor", [])),
    }


def badges_for(gem_name, class_name):
    ways = acquisition_for(gem_name, class_name)
    return ("Q" if ways["quest"] else "") + ("B" if ways["vendor"] else "")


def acquisition_html(gem_name, class_name):
    ways = acquisition_for(gem_name, class_name)
    lines = []
    if ways["quest"]:
        first = ways["quest"][0]
        lines.append(
            "<span style='color:#56e889'><b>Q · Награда за квест</b></span><br>"
            f"{first['quest']} · Акт {first['act']}"
        )
    if ways["vendor"]:
        first = ways["vendor"][0]
        lines.append(
            "<span style='color:#e1ae35'><b>B · Купить</b></span><br>"
            f"{first['npc']} · Акт {first['act']}<br>"
            f"Откроется после {first['quest']}"
        )
    if not lines:
        lines.append("<span style='color:#8f96a3'>Нет обычной награды или ранней покупки для этого класса</span>")
    return "<br><br>".join(lines)
