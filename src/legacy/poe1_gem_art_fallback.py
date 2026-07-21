"""Resolve exact gem art or a real same-kind, same-colour fallback."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).parent / "data" / "poe1"
ICON_DIR = ROOT / "gem_icons"


def _load(name):
    try:
        return json.loads((ROOT / name).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


ICON_INDEX = _load("gem_icons.json")
GEM_COLOURS = _load("gem_colors.json")

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
