import pytest
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QApplication, QWidget

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


def ordinary_route(size):
    nodes = base_tree().nodes
    route, seen = [WITCH_START], {WITCH_START}
    for node_id in route:
        for other in sorted(base_tree().graph[node_id]):
            data = nodes[other]
            if (
                other not in seen and other.isdigit() and not data.get("ascendancyName")
                and not data.get("isMastery") and data.get("classStartIndex") is None
            ):
                seen.add(other)
                route.append(other)
        if len(route) > size:
            return route[:size + 1]
    return route


def route_build(size, bandit):
    return {
        "format": "pob1", "class": "Witch", "ascendancy": "Necromancer", "gem_sets": [],
        "source_code": f'<PathOfBuilding><Build bandit="{bandit}"/></PathOfBuilding>',
        "trees": [{"level": 1, "title": "ур. 1", "nodes": [int(node) for node in ordinary_route(size)]}],
    }


@pytest.mark.parametrize("bandit, points", [("None", 24), ("Alira", 23)])
def test_bandit_point_follows_pob_choice(bandit, points):
    plan = pob_passive_plan(route_build(30, bandit), 20)

    assert len(plan["completed"]) == points + 1


class Content(QObject):
    active_step_changed = pyqtSignal()

    def get_active_step_info(self):
        return "Act 10", 0, ""


class StubOverlay(QWidget):
    def __init__(self, profile):
        super().__init__()
        self.settings = {"poe1_client_path": "missing-Client.txt"}
        self.content = Content()
        self.profile_data = {"active_profile_id": "p", "profiles": [profile]}

    def active_profile(self):
        return self.profile_data["profiles"][0]

    def save_profiles(self):
        pass

    def switch_profile(self, _):
        pass

    def create_profile(self, _):
        pass

    def _refresh_mini_tree(self):
        pass


def test_dialog_reports_unused_nodes_instead_of_next(qapp):
    from actpilot.build_dialog import CharacterRebindBuildDialog

    profile = {
        "id": "p", "name": "Ведьма", "game": "poe1", "level": 100, "campaign": {},
        "build": route_build(140, "Alira"),
    }
    dialog = CharacterRebindBuildDialog(StubOverlay(profile))

    assert dialog.tree_stage_label.text() == "Уровень персонажа 100 · не использовано нод: 18 — не хватает очков"
