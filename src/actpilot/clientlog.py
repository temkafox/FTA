"""Locale-aware, incremental parsing helpers for Path of Exile 1 Client.txt."""

from __future__ import annotations

import re
from dataclasses import dataclass


SESSION_MARKER = "***** LOG FILE OPENING *****"

# The text after the Client logger prefix is localized by the game.  Keep the
# character/class capture strict enough that unrelated chat lines cannot look
# like level-up events.
LEVEL_EVENT_PATTERN = re.compile(
    r":\s*(?P<name>[^():\r\n]+?)\s*"
    r"\((?P<class>[^()\r\n]+)\)\s*"
    r"(?:"
    r"is\s+now\s+level\s+(?P<level_en>\d{1,3})"
    r"|достигает\s+(?P<level_ru>\d{1,3})\s+уров(?:ня|ень)"
    r")(?=\s|$)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class LevelEvent:
    name: str
    character_class: str
    level: int


def parse_level_events(text: str) -> list[LevelEvent]:
    """Return valid PoE1 character level-up events in source order."""
    events = []
    for match in LEVEL_EVENT_PATTERN.finditer((text or "").replace("\x00", "")):
        raw_level = match.group("level_en") or match.group("level_ru")
        level = int(raw_level)
        if 1 <= level <= 100:
            events.append(
                LevelEvent(
                    name=match.group("name").strip(),
                    character_class=match.group("class").strip(),
                    level=level,
                )
            )
    return events


def current_session_tail(text: str) -> str:
    """Discard previous game sessions when a long Client.txt tail contains them."""
    marker = (text or "").rfind(SESSION_MARKER)
    return text[marker:] if marker >= 0 else text


def split_complete_lines(pending: str, chunk: str) -> tuple[str, str]:
    """Join a file chunk to a partial line and retain the new partial line."""
    combined = pending + chunk
    last_lf = combined.rfind("\n")
    if last_lf < 0:
        return "", combined
    return combined[: last_lf + 1], combined[last_lf + 1 :]


CLASS_ALIASES = {
    "marauder": {"marauder", "дикарь"},
    "juggernaut": {"juggernaut", "покоритель"},
    "berserker": {"berserker", "берсерк"},
    "chieftain": {"chieftain", "вождь"},
    "ranger": {"ranger", "охотница"},
    "deadeye": {"deadeye", "снайпер"},
    "raider": {"raider", "налётчик", "налетчик"},
    "pathfinder": {"pathfinder", "следопыт"},
    "witch": {"witch", "ведьма"},
    "necromancer": {"necromancer", "некромант"},
    "occultist": {"occultist", "оккультист"},
    "elementalist": {"elementalist", "маг стихий"},
    "duelist": {"duelist", "гладиатор"},
    "slayer": {"slayer", "рубaka", "рубака"},
    "gladiator": {"gladiator", "гладиатор"},
    "champion": {"champion", "защитник"},
    "templar": {"templar", "жрец"},
    "inquisitor": {"inquisitor", "инквизитор"},
    "hierophant": {"hierophant", "иезофант"},
    "guardian": {"guardian", "хранитель"},
    "shadow": {"shadow", "бандит"},
    "assassin": {"assassin", "убийца"},
    "saboteur": {"saboteur", "диверсант"},
    "trickster": {"trickster", "ловкач"},
    "scion": {"scion", "дворянка"},
    "ascendant": {"ascendant", "вознёсшаяся", "вознесшаяся"},
}


def class_matches(build_class: str, ascendancy: str, logged_class: str) -> bool:
    """Compare English build metadata with an English or Russian client locale."""
    logged = (logged_class or "").strip().casefold()
    if not logged:
        return False
    for value in (build_class, ascendancy):
        key = (value or "").strip().casefold()
        if logged == key or logged in CLASS_ALIASES.get(key, set()):
            return True
    return False
