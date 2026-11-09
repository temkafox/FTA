import pytest

from actpilot.cluster_jewels import (
    CLUSTER_NODE_MIN, JEWEL_ORDER, cluster_overlay, cluster_templates, ring_links, ring_slot,
)
from actpilot.data_cache import game_data
from actpilot.tree_model import build_tree, view_overlay

LARGE_SOCKET = "55190"
LARGE_RING = ["65696", "65697", "65698", "65699", "65705", "65706", "65707"]
MEDIUM_SOCKETS = ["49080", "44169"]


def tree():
    return game_data("skilltree.json")


def linked(overlay, first, second):
    return second in overlay.get(first, {}).get("out", []) or first in overlay.get(second, {}).get("out", [])


def reachable(start, nodes, graph):
    seen, stack = {start}, [start]
    while stack:
        for other in graph.get(stack.pop(), set()) & nodes:
            if other not in seen:
                seen.add(other)
                stack.append(other)
    return seen


def test_nested_sockets_land_on_their_tree_positions():
    nodes = tree()["nodes"]
    counts = tree()["constants"]["skillsPerOrbit"]
    templates = cluster_templates()
    checked = 0
    for node in nodes.values():
        jewel = node.get("expansionJewel", {})
        if "parent" not in jewel:
            continue
        parent = nodes[jewel["parent"]]["expansionJewel"]
        size = parent["size"]
        sockets = dict(zip(JEWEL_ORDER, templates["sizes"][str(size)]["sockets"]))
        slot = ring_slot(parent["proxy"], size, sockets[jewel["index"]], templates, counts[size + 1])

        assert (node["group"], node["orbit"], node["orbitIndex"]) == (
            nodes[parent["proxy"]]["group"], size + 1, slot,
        )
        checked += 1
    assert checked == 36


def test_large_cluster_ring_links_entrance_and_nested_sockets():
    overlay = cluster_overlay([LARGE_SOCKET, *LARGE_RING, *MEDIUM_SOCKETS])

    assert linked(overlay, "65696", LARGE_SOCKET)
    assert linked(overlay, "65699", "49080")
    assert linked(overlay, "44169", "65705")
    assert not linked(overlay, "49080", "44169")
    assert overlay["65696"]["isClusterNode"]
    assert overlay["49080"]["orbitIndex"] == tree()["nodes"]["49080"]["orbitIndex"]


def test_ring_gap_rule():
    assert (4, 8) not in ring_links([0, 1, 2, 3, 4, 8, 9, 10, 11], 12, closed=True)
    assert len(ring_links([0, 2, 4, 5, 6, 7, 8, 10], 12, closed=True)) == 8
    assert ring_links([0, 1, 2], 6, closed=False) == [(0, 1), (1, 2)]


def test_medium_cluster_directly_in_large_socket():
    index = tree()["nodes"][LARGE_SOCKET]["expansionJewel"]["index"]
    base = CLUSTER_NODE_MIN + (index << 6) + (1 << 4)
    overlay = cluster_overlay([LARGE_SOCKET, str(base), str(base + 1)])

    assert overlay[str(base)]["orbit"] == 2
    assert linked(overlay, str(base), LARGE_SOCKET)
    assert linked(overlay, str(base), str(base + 1))


def test_jewel_changed_between_stages_keeps_each_stage_connected():
    early = [LARGE_SOCKET, "65696", "65698", "65706"]
    late = [LARGE_SOCKET, *LARGE_RING, *MEDIUM_SOCKETS]
    model = build_tree([{"nodes": early}, {"nodes": late}])

    for stage in (early, late):
        assert reachable(LARGE_SOCKET, set(stage), model.graph) == set(stage)
    assert linked(view_overlay(early), "65696", "65698")
    assert not linked(view_overlay(late), "65696", "65698")


@pytest.mark.parametrize("node_id", ["30275", "49080"])
def test_structural_nodes_are_hidden_without_cluster(node_id):
    model = build_tree([])

    assert node_id not in model.nodes
    assert node_id not in model.graph
