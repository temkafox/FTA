"""Tree renderer using official GGG Russian passive descriptions."""

from poe1_tooltips_ru_v3 import OfficialRussianPassiveTooltip
from poe1_tree_renderer_v15 import RussianDescriptionTreeCanvas


class OfficialRussianTreeCanvas(RussianDescriptionTreeCanvas):
    def __init__(self, parent=None):
        super().__init__(parent)
        old = self.node_tooltip
        self.node_tooltip = OfficialRussianPassiveTooltip()
        old.deleteLater()
