"""Дерево глазами билда: дерево игры без служебных прокси-нод плюс кольца кластерных самоцветов из PoB."""

from __future__ import annotations

from functools import lru_cache
from typing import NamedTuple

from actpilot.cluster_jewels import CLUSTER_NODE_MIN, cluster_overlay
from actpilot.data_cache import game_data
from actpilot.tree_geometry import is_structural, node_point


class TreeModel(NamedTuple):
    nodes: dict
    graph: dict
    points: dict


def _adjacency(nodes):
    graph = {node_id: set() for node_id in nodes}
    for node_id, node in nodes.items():
        for other in node.get("out", []) + node.get("in", []):
            other = str(other)
            if other in graph and other != node_id:
                graph[node_id].add(other)
                graph[other].add(node_id)
    return graph


@lru_cache(maxsize=1)
def base_tree() -> TreeModel:
    data = game_data("skilltree.json")
    groups = data.get("groups", {})
    constants = data.get("constants", {})
    nodes = {
        str(node_id): node for node_id, node in data.get("nodes", {}).items()
        if not is_structural(node, groups)
    }
    points = {node_id: node_point(node, groups, constants) for node_id, node in nodes.items()}
    return TreeModel(nodes, _adjacency(nodes), points)


@lru_cache(maxsize=1)
def _structural_ids():
    data = game_data("skilltree.json")
    groups = data.get("groups", {})
    return frozenset(
        str(node_id) for node_id, node in data.get("nodes", {}).items() if is_structural(node, groups)
    )


def cluster_ids(node_ids):
    structural = _structural_ids()
    result = set()
    for node_id in node_ids:
        key = str(node_id)
        if key in structural or (key.isdigit() and int(key) >= CLUSTER_NODE_MIN):
            result.add(key)
    return frozenset(result)


@lru_cache(maxsize=32)
def _view_overlay(key):
    return cluster_overlay(key) if key else {}


def view_overlay(node_ids):
    """Кольца кластеров ровно для показываемого набора нод: у разных этапов в гнезде бывают разные самоцветы."""
    return _view_overlay(cluster_ids(node_ids))


@lru_cache(maxsize=8)
def _build_tree(keys):
    base = base_tree()
    if not keys:
        return base
    data = game_data("skilltree.json")
    groups = data.get("groups", {})
    constants = data.get("constants", {})
    overlay_nodes = {}
    links = set()
    for key in keys:
        for node_id, node in _view_overlay(key).items():
            overlay_nodes.setdefault(node_id, node)
            links.update((node_id, str(other)) for other in node.get("out", []))
    nodes = {**base.nodes, **{node_id: dict(node) for node_id, node in overlay_nodes.items()}}
    graph = {node_id: set(neighbours) for node_id, neighbours in base.graph.items()}
    for node_id in overlay_nodes:
        graph.setdefault(node_id, set())
    for first, second in links:
        if first in nodes and second in nodes:
            graph[first].add(second)
            graph[second].add(first)
    for node_id in overlay_nodes:
        nodes[node_id]["out"] = sorted(graph[node_id])
        nodes[node_id]["in"] = []
    points = dict(base.points)
    points.update(
        (node_id, node_point(node, groups, constants)) for node_id, node in overlay_nodes.items()
    )
    return TreeModel(nodes, graph, points)


def build_tree(stages) -> TreeModel:
    keys = frozenset(
        key for key in (cluster_ids(stage.get("nodes", [])) for stage in stages or []) if key
    )
    return _build_tree(keys)
