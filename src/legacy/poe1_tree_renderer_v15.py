"""Restored ascendancy tree with Russian tooltip bodies."""

from poe1_tooltips_ru import RussianPassiveTooltip
from poe1_tree_renderer_v14 import RestoredAscendancyTreeCanvas


class RussianDescriptionTreeCanvas(RestoredAscendancyTreeCanvas):
    def __init__(self, parent=None):
        super().__init__(parent)
        for node_id, node in self.nodes.items():
            node["_id"] = str(node_id)
        self.node_tooltip.hide()
        self.node_tooltip.deleteLater()
        self.node_tooltip = RussianPassiveTooltip()
