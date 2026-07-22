"""Совместимость: живой канвас переехал в actpilot.tree; здесь остался placeholder."""

from __future__ import annotations

from PyQt5.QtCore import QPointF
from PyQt5.QtWidgets import QWidget

from actpilot.tree import CachedZoomSafeTreeCanvas


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
