"""Геометрия пассивного дерева PoE 1: углы орбит, мировые координаты нод, служебные прокси-ноды."""

from __future__ import annotations

import math

# skilltree-export 3.17.0: 16 слотов — шаг 30° с добавкой 45°; 40 слотов — шаг 10° с добавкой 45° (как в Path of Building)
ORBIT_DEGREES = {
    16: (0, 30, 45, 60, 90, 120, 135, 150, 180, 210, 225, 240, 270, 300, 315, 330),
    40: tuple(sorted(set(range(0, 360, 10)) | {45, 135, 225, 315})),
}


def orbit_angle(index, count):
    degrees = ORBIT_DEGREES.get(count)
    if degrees is not None and 0 <= index < len(degrees):
        return math.radians(degrees[index])
    return 2 * math.pi * index / max(1, count)


def orbit_point(center_x, center_y, orbit, index, radii, counts):
    radius = radii[orbit] if orbit < len(radii) else 0
    count = counts[orbit] if orbit < len(counts) else 1
    angle = orbit_angle(index, count)
    return center_x + radius * math.sin(angle), center_y - radius * math.cos(angle)


def node_point(node, groups, constants):
    group = groups.get(str(node.get("group")), {})
    return orbit_point(
        float(group.get("x", 0)),
        float(group.get("y", 0)),
        int(node.get("orbit", 0)),
        int(node.get("orbitIndex", 0)),
        constants.get("orbitRadii", []),
        constants.get("skillsPerOrbit", []),
    )


def is_structural(node, groups):
    # Прокси и гнёзда внутри прокси-групп существуют только как часть вставленного кластерного самоцвета
    return bool(node.get("isProxy") or groups.get(str(node.get("group")), {}).get("isProxy"))
