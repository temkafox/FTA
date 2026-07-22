"""Совместимость: модуль переехал в actpilot.build_model."""

from actpilot.build_model import (
    ASCENDANCIES,
    CLASS_START_INDEX,
    LAB_LEVELS,
    ROOT,
    TREE_FILE,
    ascendancy_budget,
    ascendancy_start_id,
    class_start_id,
    load_tree,
    passive_budget,
)
from actpilot.build_model import build_from_state_v2 as build_from_state
from actpilot.build_model import state_from_build_v1 as state_from_build
