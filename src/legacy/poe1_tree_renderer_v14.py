"""Native ascendancy renderer with mandatory coordinate restoration."""

from __future__ import annotations

import json
import math

from PyQt5.QtCore import QPointF

from poe1_tree_renderer_v13 import NativeAscendancyTreeCanvas
from poe1_widgets import TREE_FILE


class RestoredAscendancyTreeCanvas(NativeAscendancyTreeCanvas):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._restore_ascendancy_positions()

    def _restore_ascendancy_positions(self):
        try:
            data = json.loads(TREE_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        groups = data.get("groups", {})
        constants = data.get("constants", {})
        radii = constants.get("orbitRadii", [])
        counts = constants.get("skillsPerOrbit", [])
        for node_id, node in data.get("nodes", {}).items():
            if not node.get("ascendancyName"):
                continue
            group = groups.get(str(node.get("group")), {})
            orbit = int(node.get("orbit", 0))
            index = int(node.get("orbitIndex", 0))
            radius = radii[orbit] if orbit < len(radii) else 0
            count = counts[orbit] if orbit < len(counts) else 1
            angle = 2 * math.pi * index / max(1, count)
            self.positions[str(node_id)] = QPointF(
                float(group.get("x", 0)) + radius * math.sin(angle),
                float(group.get("y", 0)) - radius * math.cos(angle),
            )
