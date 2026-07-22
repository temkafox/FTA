"""Совместимость: модуль переехал в actpilot.clientlog."""

from actpilot.clientlog import (
    CLASS_ALIASES,
    LEVEL_EVENT_PATTERN,
    LevelEvent,
    SESSION_MARKER,
    class_matches,
    current_session_tail,
    parse_level_events,
    split_complete_lines,
)
