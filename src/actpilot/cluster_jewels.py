"""Кольца кластерных самоцветов из PoB-билда по алгоритму PassiveSpec:BuildSubgraph (Path of Building).

PoB пишет ноды кластера синтетическими id: бит 16 — признак, биты 0-3 — индекс в шаблоне кольца,
4-5 — размер кластера, 6-8 — номер большого гнезда, 9-10 — номер среднего гнезда внутри большого кластера.
"""

from __future__ import annotations

from actpilot.data_cache import game_data

CLUSTER_NODE_MIN = 0x10000
# PoB раскладывает вложенные гнёзда по socketIndicies в порядке номеров самоцветов 0, 2, 1
JEWEL_ORDER = (0, 2, 1)
TEMPLATE_TO_ORBIT = {
    (12, 16): (0, 1, 3, 4, 5, 7, 8, 9, 11, 12, 13, 15),
    (6, 16): (0, 3, 5, 8, 11, 13),
}
CLUSTER_NODE_NAME = "Пассив кластерного самоцвета"
CLUSTER_NODE_STATS = ("Свойства задаёт сам самоцвет: в экспорте PoB есть только номер ноды",)


def cluster_templates():
    return game_data("cluster_jewels.json")


def template_to_orbit(index, total, slots):
    if total == slots:
        return index
    table = TEMPLATE_TO_ORBIT.get((total, slots))
    return table[index] if table else index * slots // total


def ring_slot(proxy_id, size, template_index, templates, slots):
    offset = templates.get("orbit_offsets", {}).get(str(proxy_id), {}).get(str(size))
    if offset is None:
        return None
    total = templates["sizes"][str(size)]["total"]
    return template_to_orbit((template_index + offset) % total, total, slots)


def ring_links(indexes, total, closed):
    links = list(zip(indexes, indexes[1:]))
    if closed and len(indexes) > 2:
        links.append((indexes[-1], indexes[0]))
        gaps = [(second - first) % total for first, second in links]
        # Невзятые ноды кольца неизвестны: рвём единственный самый большой пропуск, ровное кольцо замкнуто целиком
        if gaps.count(max(gaps)) == 1:
            del links[gaps.index(max(gaps))]
    return links


def _cluster_pool(ids):
    pool = {}
    for node_id in ids:
        try:
            value = int(node_id)
        except ValueError:
            continue
        if value >= CLUSTER_NODE_MIN:
            pool.setdefault((value & ~0x3F, (value >> 4) & 3), {})[value & 0xF] = node_id
    return pool


def cluster_overlay(node_ids, data=None, templates=None):
    """Ноды, которые добавляются в дерево (кольца) или заменяют свои копии в нём (гнёзда с новыми связями)."""
    data = data if data is not None else game_data("skilltree.json")
    templates = templates if templates is not None else cluster_templates()
    nodes = data.get("nodes", {})
    groups = data.get("groups", {})
    counts = data.get("constants", {}).get("skillsPerOrbit", [])
    ids = {str(node_id) for node_id in node_ids}
    pool = _cluster_pool(ids)
    if not pool or not templates.get("sizes"):
        return {}

    overlay = {}
    links = []

    def tree_node_copy(node_id, keep_links=True):
        if node_id not in overlay:
            node = nodes[node_id]
            overlay[node_id] = dict(node, _id=node_id)
            overlay[node_id]["out"] = list(node.get("out", [])) if keep_links else []
            overlay[node_id]["in"] = list(node.get("in", [])) if keep_links else []
        return overlay[node_id]

    def nested_socket(group_id, jewel_index):
        return next(
            (
                str(other) for other in groups.get(group_id, {}).get("nodes", [])
                if nodes.get(str(other), {}).get("expansionJewel", {}).get("index") == jewel_index
            ),
            None,
        )

    def build(socket_id, base, socket_size):
        size = next((size for size in range(socket_size, -1, -1) if (base, size) in pool), None)
        if size is None:
            return
        proxy_id = str(nodes[socket_id].get("expansionJewel", {}).get("proxy", ""))
        orbit = size + 1
        if (
            proxy_id not in nodes
            or orbit >= len(counts)
            or ring_slot(proxy_id, size, 0, templates, counts[orbit]) is None
        ):
            return
        template = templates["sizes"][str(size)]
        group_id = str(nodes[proxy_id].get("group"))
        members = dict(pool.pop((base, size)))
        nested = {}
        for jewel_index, template_index in zip(JEWEL_ORDER, template["sockets"]):
            nested_id = nested_socket(group_id, jewel_index)
            if nested_id in ids and template_index not in members:
                members[template_index] = nested_id
                nested[nested_id] = jewel_index

        for template_index, node_id in members.items():
            if node_id in nested:
                tree_node_copy(node_id, keep_links=False)
                continue
            overlay[node_id] = {
                "_id": node_id,
                "name": CLUSTER_NODE_NAME,
                "stats": list(CLUSTER_NODE_STATS),
                "group": group_id,
                "orbit": orbit,
                "orbitIndex": ring_slot(proxy_id, size, template_index, templates, counts[orbit]),
                "out": [],
                "in": [],
                "isClusterNode": True,
            }
        indexes = sorted(members)
        links.extend(
            (members[first], members[second])
            for first, second in ring_links(indexes, template["total"], closed=size > 0)
        )
        if 0 in members:
            links.append((members[0], socket_id))
        for nested_id, jewel_index in nested.items():
            nested_size = nodes[nested_id].get("expansionJewel", {}).get("size", 0)
            build(nested_id, base + (jewel_index << 9 if nested_size == 1 else 0), nested_size)

    for socket_id, socket in nodes.items():
        jewel = socket.get("expansionJewel")
        if jewel and jewel.get("size") == 2 and "parent" not in jewel:
            build(str(socket_id), CLUSTER_NODE_MIN + (int(jewel.get("index", 0)) << 6), 2)

    for first, second in links:
        tree_node_copy(second)
        overlay[first]["out"].append(second)
        overlay[second]["in"].append(first)
    return overlay
