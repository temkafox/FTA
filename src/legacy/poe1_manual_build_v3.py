"""Manual build model with an exact ordinary/mastery allocation order."""

from __future__ import annotations

import copy

import poe1_manual_build as base
import poe1_manual_build_v2 as previous
from poe1_manual_build import *  # noqa: F401,F403


def state_from_build(build, level=1):
    state = base.state_from_build(build, level)
    if not state.get("allocation_order"):
        state["allocation_order"] = (
            [str(node) for node in state.get("passives", [])]
            + [str(node) for node in state.get("masteries", {})]
        )
    return state


def build_from_state(state):
    state = copy.deepcopy(state)
    order = [str(node) for node in state.get("allocation_order", [])]
    known = {str(node) for node in state.get("passives", [])} | {
        str(node) for node in state.get("masteries", {})
    }
    order = [node for node in order if node in known]
    for node in list(state.get("passives", [])) + list(state.get("masteries", {})):
        node = str(node)
        if node not in order:
            order.append(node)
    state["allocation_order"] = order
    result = previous.build_from_state(state)

    nodes = base.load_tree().get("nodes", {})
    start = base.class_start_id(nodes, state.get("class", "Witch"))
    regular = [start] + order
    for tree in result.get("trees", []):
        ascendancy = [
            str(node) for node in tree.get("nodes", [])
            if nodes.get(str(node), {}).get("ascendancyName")
        ]
        if len(tree.get("nodes", [])) > 2:
            tree["nodes"] = regular + ascendancy
    result["manual_editor"] = copy.deepcopy(state)
    return result
