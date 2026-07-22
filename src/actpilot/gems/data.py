"""Данные гемов PoE1: получение по классам, уровни, оффлайн-арт."""

from __future__ import annotations

import copy

from actpilot.data_cache import game_data
from actpilot.paths import get_resource_dir


DATA = game_data("gem_acquisition.json").get("gems", {})


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


GEM_LEVELS = game_data("gem_levels.json")


def effective_gem_level(name, character_level, imported_level=None):
    data = GEM_LEVELS.get((name or "").casefold())
    if not data:
        return imported_level
    try:
        cap = int(imported_level) if imported_level else 20
    except (TypeError, ValueError):
        cap = 20
    available = [
        int(gem_level)
        for gem_level, requirement in data.get("requirements", {}).items()
        if int(gem_level) <= cap and int(requirement) <= int(character_level)
    ]
    return max(available) if available else None


def links_at_level(links, character_level):
    scaled_links = []
    for link in links:
        scaled_gems = []
        for gem in link.get("gems", []):
            scaled_level = effective_gem_level(
                gem.get("name", ""), character_level, gem.get("level")
            )
            known = (gem.get("name") or "").casefold() in GEM_LEVELS
            if known and scaled_level is None:
                continue
            scaled = copy.deepcopy(gem)
            if scaled_level is not None:
                scaled["level"] = str(scaled_level)
            scaled_gems.append(scaled)
        if scaled_gems:
            scaled_link = copy.deepcopy(link)
            scaled_link["gems"] = scaled_gems
            scaled_links.append(scaled_link)
    return scaled_links


# Прежде ROOT считался от __file__ модуля; get_resource_dir() даёт тот же каталог
ROOT = get_resource_dir() / "data" / "poe1"
ICON_DIR = ROOT / "gem_icons"

ICON_INDEX = game_data("gem_icons.json")
GEM_COLOURS = game_data("gem_colors.json")

# These are deliberately explicit: names such as Arcane Surge do not contain
# "Support", so guessing the kind from a filename is unreliable.
FALLBACK_NAMES = {
    ("red", False): "absolution",
    ("red", True): "added fire damage",
    ("green", False): "blink arrow",
    ("green", True): "faster attacks",
    ("blue", False): "rolling magma",
    ("blue", True): "immolate",
}


def gem_colour(name):
    return GEM_COLOURS.get((name or "").strip().casefold(), "blue")


def _indexed_path(name):
    info = ICON_INDEX.get((name or "").strip().casefold(), {})
    filename = info.get("file", "")
    path = ICON_DIR / filename if filename else None
    return path if path and path.is_file() else None


def gem_art_path(gem):
    """Return exact art, or real art matching both colour and gem kind."""
    exact = _indexed_path(gem.get("name", ""))
    if exact:
        return exact
    key = (gem_colour(gem.get("name", "")), bool(gem.get("support")))
    fallback = _indexed_path(FALLBACK_NAMES.get(key, ""))
    if fallback:
        return fallback
    # Last-resort colour fallback is still real artwork, never a letter badge.
    for (colour, _support), name in FALLBACK_NAMES.items():
        if colour == key[0]:
            fallback = _indexed_path(name)
            if fallback:
                return fallback
    return None
