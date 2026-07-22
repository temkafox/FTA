"""Единый кеш игровых JSON: каждый файл парсится один раз на процесс."""

import json
import sys
from functools import lru_cache
from pathlib import Path

from actpilot.paths import get_resource_dir


def _game_file(name: str) -> Path:
    return get_resource_dir() / "data" / "poe1" / name


@lru_cache(maxsize=None)
def _load(path_str: str):
    return json.loads(Path(path_str).read_text(encoding="utf-8"))


def load_file(path, default=None):
    try:
        return _load(str(Path(path).resolve()))
    except (OSError, ValueError) as exc:
        print(f"ActPilot: не удалось загрузить {Path(path).name}: {exc}", file=sys.stderr)
        return {} if default is None else default


def game_data(name: str, default=None):
    return load_file(_game_file(name), default)


@lru_cache(maxsize=None)
def _tree_graph(path_str: str) -> dict:
    # Сырое дерево (6.5 МБ) парсится транзитно: в кеше остаётся только граф
    try:
        nodes = json.loads(Path(path_str).read_text(encoding="utf-8")).get("nodes", {})
    except (OSError, ValueError) as exc:
        print(f"ActPilot: не удалось построить дерево: {exc}", file=sys.stderr)
        return {}
    graph = {str(node_id): set() for node_id in nodes}
    for node_id, node in nodes.items():
        first = str(node_id)
        for other in node.get("out", []) + node.get("in", []):
            second = str(other)
            if second in graph:
                graph[first].add(second)
                graph[second].add(first)
    return graph


def tree_graph(path=None) -> dict:
    target = Path(path) if path is not None else _game_file("skilltree.json")
    try:
        key = str(target.resolve())
    except OSError:
        key = str(target)
    return _tree_graph(key)
