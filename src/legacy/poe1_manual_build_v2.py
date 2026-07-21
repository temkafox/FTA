"""Compatibility fixes for the manual build serializer."""

from __future__ import annotations

import poe1_manual_build as base
from poe1_manual_build import *  # noqa: F401,F403


def build_from_state(state):
    result = base.build_from_state(state)
    effects = {
        str(node): effect for node, effect in state.get("masteries", {}).items() if effect
    }
    raw = ",".join(f"{{{node},{effect}}}" for node, effect in effects.items())
    for tree in result.get("trees", []):
        if len(tree.get("nodes", [])) > 2:
            tree["masteries"] = raw
    return result
