"""Совместимость: модуль переехал в actpilot.build_model."""

from actpilot.build_model import (
    SNAPSHOT_KEYS,
    ascendancy_start_id,
    class_start_id,
    load_tree,
    normalize_passive_stages,
)
from actpilot.build_model import build_from_state_v4 as build_from_state
from actpilot.build_model import state_from_build_v4 as state_from_build
