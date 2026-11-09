import pytest
from PyQt5.QtWidgets import QApplication

from actpilot.level_plans import quest_aware_passive_plan


START = "54447"


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def make_graph(*edges):
    graph = {}
    for first, second in edges:
        graph.setdefault(first, set()).add(second)
        graph.setdefault(second, set()).add(first)
    return graph


def stage(level, title, nodes, masteries=""):
    return {"level": level, "title": title, "nodes": list(nodes), "masteries": masteries}


def plan_at(stages, level, graph):
    return quest_aware_passive_plan(stages, level, graph, False)


def connected_from_start(nodes, graph):
    nodes = set(nodes)
    seen = {START} & nodes
    stack = list(seen)
    while stack:
        for other in graph.get(stack.pop(), set()) & nodes:
            if other not in seen:
                seen.add(other)
                stack.append(other)
    return seen == nodes


RESPEC_GRAPH = make_graph(
    (START, "s1"),
    ("s1", "x1"), ("x1", "x2"), ("x2", "hub"),
    (START, "y1"), ("y1", "y2"), ("y2", "hub"),
    ("hub", "k1"), ("k1", "k2"), ("k2", "n1"),
)
OLD_TREE = stage(1, "Акт 1 · ур. 1-6", [START, "s1", "x1", "x2", "hub", "k1", "k2"], "{100,1}")
RESPEC_TREE = stage(
    10, "Респек · ур. 10", [START, "s1", "y1", "y2", "hub", "k1", "k2", "n1"], "{100,2},{200,3}",
)


def test_class_start_is_free_and_route_starts_from_it():
    graph = make_graph((START, "a1"), ("a1", "a2"))
    plan = plan_at([stage(1, "ур. 1", ["a2", "a1", START])], 1, graph)

    assert plan["completed"] == [START]
    assert plan["upcoming"] == ["a1", "a2"]
    assert plan["node_levels"] == {"a1": 2, "a2": 3}


def test_additive_stages_continue_point_count():
    graph = make_graph((START, "a1"), ("a1", "a2"), ("a2", "a3"), ("a3", "a4"))
    stages = [
        stage(1, "ур. 1", [START, "a1", "a2"]),
        stage(2, "ур. 2", [START, "a1", "a2", "a3", "a4"]),
    ]
    plan = plan_at(stages, 3, graph)

    assert plan["target"] is stages[1]
    assert plan["completed"] == [START, "a1", "a2"]
    assert plan["upcoming"] == ["a3", "a4"]
    assert plan["node_levels"] == {"a3": 4, "a4": 5}
    assert plan["respec"] is None


def test_respec_waits_for_stage_level_and_keeps_old_tree_whole():
    stages = [OLD_TREE, RESPEC_TREE]
    plan = plan_at(stages, 6, RESPEC_GRAPH)

    assert plan["target"]["title"] == OLD_TREE["title"]
    assert set(plan["completed"]) == set(OLD_TREE["nodes"])
    assert plan["upcoming"] == ["y1", "y2", "n1"]
    assert plan["node_levels"] == {"x1": 3, "x2": 4, "hub": 5, "k1": 5, "k2": 6, "s1": 2, "y1": 7, "y2": 8, "n1": 9}
    assert plan["respec"]["level"] == 10
    assert plan["respec"]["refund"] == ["x1", "x2"]
    assert plan["target"]["masteries"] == "{100,1},{200,3}"


def test_spare_points_before_respec_go_to_reachable_new_nodes():
    plan = plan_at([OLD_TREE, RESPEC_TREE], 9, RESPEC_GRAPH)

    assert set(plan["completed"]) == set(OLD_TREE["nodes"]) | {"y1", "y2", "n1"}
    assert plan["upcoming"] == []
    assert plan["respec"]["refund"] == ["x1", "x2"]


def test_respec_level_switches_tree_and_reports_refund_once():
    stages = [OLD_TREE, RESPEC_TREE]
    at_respec = plan_at(stages, 10, RESPEC_GRAPH)
    after = plan_at(stages, 11, RESPEC_GRAPH)

    assert at_respec["target"] is RESPEC_TREE
    assert set(at_respec["completed"]) == set(RESPEC_TREE["nodes"])
    assert at_respec["respec"] == {"level": 10, "title": RESPEC_TREE["title"], "refund": ["x1", "x2"]}
    assert after["respec"] is None
    assert set(after["completed"]) == set(RESPEC_TREE["nodes"])


def test_allocated_nodes_stay_connected_on_every_level():
    stages = [OLD_TREE, RESPEC_TREE]
    for level in range(1, 21):
        plan = plan_at(stages, level, RESPEC_GRAPH)
        assert connected_from_start(plan["completed"], RESPEC_GRAPH), level


def test_respec_returns_refunded_points():
    chain = [START] + [f"a{index}" for index in range(1, 9)]
    graph = make_graph(*zip(chain, chain[1:]), ("a4", "b1"), ("b1", "b2"), ("b2", "b3"), ("b3", "b4"))
    stages = [
        stage(1, "ур. 1", chain),
        stage(9, "ур. 9", chain[:5] + ["b1", "b2", "b3", "b4"]),
    ]
    plan = plan_at(stages, 9, graph)

    assert set(plan["completed"]) == set(stages[1]["nodes"])
    assert plan["upcoming"] == []
    assert plan["node_markers"]["b4"] == "9Р"


def test_respec_before_previous_tree_is_complete():
    chain = [START] + [f"a{index}" for index in range(1, 7)]
    graph = make_graph(*zip(chain, chain[1:]), ("a1", "b1"), ("b1", "b2"))
    stages = [
        stage(1, "ур. 1", chain),
        stage(4, "ур. 4", [START, "a1", "b1", "b2"]),
    ]
    before = plan_at(stages, 3, graph)
    at_respec = plan_at(stages, 4, graph)

    assert before["completed"] == [START, "a1", "a2"]
    assert before["planned"] == [START, "a1", "a2"]
    assert before["respec"]["refund"] == ["a2"]
    assert set(at_respec["completed"]) == {START, "a1", "b1", "b2"}
    assert at_respec["respec"]["refund"] == ["a2"]


def test_canvas_draws_and_focuses_refund_nodes(qapp):
    from actpilot.tree import CachedZoomSafeTreeCanvas

    canvas = CachedZoomSafeTreeCanvas()
    canvas.resize(640, 480)
    canvas.set_quest_progression([START], [START], [], {}, {})
    canvas.set_refund_nodes(["57264", 33296])

    assert canvas.refund_nodes == {"57264", "33296"}
    assert canvas.immediate_focus_nodes() == {"57264", "33296"}
    assert not canvas.grab().isNull()


def test_nodes_beyond_last_level_are_unreachable_not_upcoming():
    chain = [START] + [f"c{index}" for index in range(1, 131)]
    graph = make_graph(*zip(chain, chain[1:]))
    plan = plan_at([stage(1, "ур. 1", chain)], 100, graph)

    assert plan["upcoming"] == []
    assert plan["unreachable"] == chain[123:]
    assert len(plan["completed"]) == 123
