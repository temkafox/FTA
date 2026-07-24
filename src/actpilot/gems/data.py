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


def _acquisition_record(gem_name, support=None):
    """Path of Building пишет имя саппорта без суффикса, справочник хранит его с суффиксом."""
    key = (gem_name or "").strip().casefold()
    if not key:
        return {}
    candidates = [f"{key} support", key] if support else [key, f"{key} support"]
    if key.endswith(" support"):
        candidates.append(key[: -len(" support")])
    for candidate in candidates:
        record = DATA.get(candidate)
        if record:
            return record
    return {}


def acquisition_for(gem_name, class_name, support=None):
    record = _acquisition_record(gem_name, support)
    ways = record.get("classes", {}).get(normalized_class(class_name), {})
    return {
        "quest": list(ways.get("quest", [])),
        "vendor": list(ways.get("vendor", [])),
    }


def badges_for(gem_name, class_name, support=None):
    ways = acquisition_for(gem_name, class_name, support)
    return ("Q" if ways["quest"] else "") + ("B" if ways["vendor"] else "")


def acquisition_html(gem_name, class_name, support=None):
    ways = acquisition_for(gem_name, class_name, support)
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


# PoB держит умения от предметов и пассивов в той же секции, что и связки камней
GRANTED_NON_GEMS = {
    "primal aegis",
}


def required_level(name):
    record = GEM_LEVELS.get((name or "").strip().casefold(), {})
    try:
        return int(record.get("requirements", {}).get("1"))
    except (TypeError, ValueError):
        return None


GEM_CATALOG = game_data("gem_catalog.json")
RU_GEM_NAMES = game_data("ru_descriptions.json", {"gems": {}}).get("gems", {})


def is_support_gem(name):
    """Тип камня по имени: импорт PoB берёт его из skillId, ручной ввод — отсюда.

    Триггерные камни вроде Spellslinger дают и умение, и поддержку; здесь они
    считаются поддержкой, в импорте PoB — активными.
    """
    key = (name or "").strip().casefold()
    if not key:
        return False
    if key.endswith(" support"):
        return True
    # У неоднозначных имён (Barrage) поддержка лежит в каталоге отдельной записью
    if f"{key} support" in GEM_CATALOG:
        return False
    description = (GEM_CATALOG.get(key, {}).get("description") or "").strip().lower()
    if description.startswith("support"):
        return True
    return f"{key} support" in RU_GEM_NAMES or f"{key} support" in DATA


def link_to_text(link):
    names = [str(gem.get("name", "")).strip() for gem in (link or {}).get("gems", [])]
    return ", ".join(name for name in names if name)


def links_to_text(links):
    lines = [link_to_text(link) for link in links or []]
    return "\n".join(line for line in lines if line)


def locked_gems(links, character_level):
    """Камни набора, недоступные на этом уровне: [(имя, требуемый уровень), ...]."""
    locked = []
    for link in links or []:
        for gem in link.get("gems", []):
            name = gem.get("name", "")
            if (name or "").casefold() in GRANTED_NON_GEMS:
                continue
            if effective_gem_level(name, character_level, gem.get("level")) is not None:
                continue
            requirement = required_level(name)
            if requirement is not None:
                locked.append((name, requirement))
    return sorted(locked, key=lambda item: item[1])


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
