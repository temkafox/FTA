"""Single-pass, cached construction for the current PoE 1 passive tree."""

from __future__ import annotations

import json
import math
from pathlib import Path

from PyQt5.QtCore import QPointF, QRectF
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QSizePolicy, QWidget

from poe1_tooltips_ru_v3 import OfficialRussianPassiveTooltip
from poe1_tree_renderer_v20 import ZoomSafeTreeCanvas


ROOT = Path(__file__).parent / "data" / "poe1"
TREE_FILE = ROOT / "skilltree.json"


class ConstructionTreePlaceholder(QWidget):
    """Cheap API-compatible canvas used only while legacy UI layers initialise."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.nodes = {}
        self.positions = {}
        self.edges = []
        self.selected = set()
        self.added = set()
        self.selected_masteries = {}
        self.completed_nodes = set()
        self.route_nodes = set()
        self.next_nodes = set()
        self.completed_masteries = set()
        self.next_mastery = None
        self.progression_edges = set()
        self.ascendancy = {"nodes": [], "edges": [], "completed": [], "next": []}
        self.center = QPointF()
        self.scale = 0.035

    def set_stage(self, nodes, previous_nodes=None):
        self.selected = {str(node) for node in nodes}
        previous = {str(node) for node in (previous_nodes or [])}
        self.added = self.selected - previous

    def set_progression(self, planned, completed, upcoming):
        self.selected = {str(node) for node in planned}
        self.completed_nodes = {str(node) for node in completed}
        self.route_nodes = self.selected - self.completed_nodes
        self.next_nodes = {str(node) for node in upcoming[:1]}

    def set_level_progression(self, planned, completed, upcoming, node_levels):
        self.set_progression(planned, completed, upcoming)

    def set_quest_progression(self, planned, completed, upcoming, node_levels, node_markers):
        self.set_progression(planned, completed, upcoming)

    def set_masteries(self, raw):
        return None

    def set_mastery_progression(self, completed, next_node=None):
        self.completed_masteries = {str(node) for node in completed}
        self.next_mastery = str(next_node) if next_node is not None else None

    def set_ascendancy_build(self, build, level):
        return None

    def fit_all(self):
        return None

    def fit_selected(self):
        return None

    def fit_upcoming(self):
        return None

    def fit_ascendancy(self):
        return None


class CachedZoomSafeTreeCanvas(ZoomSafeTreeCanvas):
    """Final renderer initialised directly instead of through 15 ancestors."""

    _tree_data = None
    _active_sprite = None
    _inactive_sprite = None

    @classmethod
    def _shared_data(cls):
        if cls._tree_data is None:
            cls._tree_data = json.loads(TREE_FILE.read_text(encoding="utf-8"))
        return cls._tree_data

    @classmethod
    def _shared_sprites(cls):
        if cls._active_sprite is None:
            cls._active_sprite = QPixmap(str(ROOT / "skills-2.jpg"))
            cls._inactive_sprite = QPixmap(str(ROOT / "skills-disabled-2.jpg"))
        return cls._active_sprite, cls._inactive_sprite

    def __init__(self, parent=None):
        # Deliberately call QWidget directly. The inherited constructor chain
        # parses the same 6.5 MB payload three times and rebuilds edges twice.
        QWidget.__init__(self, parent)
        self.setMinimumSize(520, 390)
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        data = self._shared_data()
        self.nodes = data.get("nodes", {})
        self.positions = {}
        self.edges = []
        self.selected = set()
        self.added = set()
        self.center = QPointF(0, 0)
        self.scale = 0.035
        self._drag_start = None

        groups = data.get("groups", {})
        constants = data.get("constants", {})
        radii = constants.get("orbitRadii", [])
        counts = constants.get("skillsPerOrbit", [])
        self.group_centers = {
            str(group_id): QPointF(float(group.get("x", 0)), float(group.get("y", 0)))
            for group_id, group in groups.items()
        }
        self.orbit_radii = radii
        self.orbit_counts = counts

        ascendancy_ids = set()
        for node_id, node in self.nodes.items():
            key = str(node_id)
            node["_id"] = key
            group = groups.get(str(node.get("group")), {})
            orbit = int(node.get("orbit", 0))
            index = int(node.get("orbitIndex", 0))
            radius = radii[orbit] if orbit < len(radii) else 0
            count = counts[orbit] if orbit < len(counts) else 1
            angle = 2 * math.pi * index / max(1, count)
            self.positions[key] = QPointF(
                float(group.get("x", 0)) + radius * math.sin(angle),
                float(group.get("y", 0)) - radius * math.cos(angle),
            )
            if node.get("ascendancyName") or node.get("isAscendancyStart"):
                ascendancy_ids.add(key)

        # Reconstruct complete ordinary-tree edges once. Ascendancy and
        # mastery connections are rendered by their dedicated layers.
        edges = set()
        for node_id, node in self.nodes.items():
            first = str(node_id)
            if first in ascendancy_ids or node.get("isMastery"):
                continue
            for other in node.get("out", []) + node.get("in", []):
                second = str(other)
                other_node = self.nodes.get(second, {})
                if (
                    second == first
                    or second not in self.positions
                    or second in ascendancy_ids
                    or other_node.get("isMastery")
                ):
                    continue
                edges.add(tuple(sorted((first, second))))
        self.edges = sorted(edges)

        self.active_sprite, self.inactive_sprite = self._shared_sprites()
        self.sprite_coords = {"active": {}, "inactive": {}}
        zoom_key = "0.2972"
        for source_key, target_key in (
            ("normalActive", "active"), ("notableActive", "active"),
            ("keystoneActive", "active"), ("normalInactive", "inactive"),
            ("notableInactive", "inactive"), ("keystoneInactive", "inactive"),
        ):
            group = data.get("sprites", {}).get(source_key, {}).get(zoom_key, {})
            self.sprite_coords[target_key].update(group.get("coords", {}))

        self.selected_masteries = {}
        self.node_tooltip = OfficialRussianPassiveTooltip()
        self.node_levels = {}
        self.node_markers = {}
        self.upcoming_order = []
        self.preview_nodes = set()
        self.completed_nodes = set()
        self.route_nodes = set()
        self.next_nodes = set()
        self.mastery_ids = {
            node_id for node_id, node in self.nodes.items() if node.get("isMastery")
        }
        self.completed_masteries = set()
        self.next_mastery = None
        self.progression_edges = set()
        self.ascendancy = {
            "name": "Ассенданси", "nodes": [], "edges": [], "completed": [], "next": [],
        }
        self._asc_screen = {}
        self._asc_panel = QRectF()

