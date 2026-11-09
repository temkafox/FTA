import pytest
from PyQt5.QtWidgets import QApplication

from actpilot.level_plans import pob_passive_plan
from actpilot.tree_model import base_tree, view_overlay

WITCH_START = "54447"
SPELL_DAMAGE_AND_MANA = "57264"
SPELL_DAMAGE = "33296"
NECROMANCER_START = "60791"


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def witch_build():
    nodes = base_tree().nodes
    ascendancy = next(
        other for other in sorted(base_tree().graph[NECROMANCER_START])
        if nodes[other].get("ascendancyName") == "Necromancer"
    )
    return {
        "format": "pob1",
        "trees": [{
            "level": 1, "title": "ур. 1",
            "nodes": [
                int(WITCH_START), int(NECROMANCER_START), int(ascendancy),
                int(SPELL_DAMAGE_AND_MANA), int(SPELL_DAMAGE),
            ],
        }],
    }


def test_ascendancy_nodes_do_not_spend_main_tree_points():
    plan = pob_passive_plan(witch_build(), 1)

    assert plan["completed"] == [WITCH_START]
    assert plan["upcoming"] == [SPELL_DAMAGE_AND_MANA, SPELL_DAMAGE]


def test_mini_route_follows_the_same_plan(qapp):
    from actpilot.minipanels import MiniPassiveRoute

    mini = MiniPassiveRoute()
    mini.set_build_level(witch_build(), 1)

    assert mini._focus_node == SPELL_DAMAGE_AND_MANA


def test_canvas_cluster_overlay_round_trip(qapp):
    from actpilot.tree import CachedZoomSafeTreeCanvas

    canvas = CachedZoomSafeTreeCanvas()
    edges = list(canvas.edges)
    assert "30275" not in canvas.positions and "49080" not in canvas.positions

    canvas.set_cluster_overlay(view_overlay(["55190", "65696", "65697", "65698", "65699", "49080"]))
    assert {"65696", "49080"} <= set(canvas.positions)
    assert ("55190", "65696") in canvas.edges
    assert ("49080", "65699") in canvas.edges

    canvas.set_cluster_overlay({})
    assert "65696" not in canvas.positions and "49080" not in canvas.positions
    assert canvas.edges == edges
