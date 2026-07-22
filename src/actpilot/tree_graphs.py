"""Кеш графа дерева для build_dialog: TREE_GRAPH из бывших main_poe1_target_v2/v3."""

from __future__ import annotations

import sys

from actpilot.data_cache import tree_graph
from actpilot.paths import get_resource_dir


TREE_FILE = get_resource_dir() / "data" / "poe1" / "skilltree.json"
TREE_GRAPH = tree_graph(TREE_FILE)

# build_dialog зовёт `v3.per_level.TREE_GRAPH`: v3 и per_level указывают на этот модуль
per_level = sys.modules[__name__]
