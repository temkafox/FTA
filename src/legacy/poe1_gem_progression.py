"""Scale PoB gem links to the current character level."""

from __future__ import annotations

import copy
import json
from pathlib import Path


LEVEL_FILE = Path(__file__).parent / "data" / "poe1" / "gem_levels.json"
try:
    GEM_LEVELS = json.loads(LEVEL_FILE.read_text(encoding="utf-8"))
except (OSError, ValueError):
    GEM_LEVELS = {}


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
