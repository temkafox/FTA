"""Russian passive tooltip; RussianGemTooltip переехал в actpilot.gems.widgets."""

from __future__ import annotations

from actpilot.gems.widgets import RussianGemTooltip
from poe1_ru_text import localized_node
from poe1_tree_renderer_v4 import OpaqueMasteryTooltip


class RussianPassiveTooltip(OpaqueMasteryTooltip):
    def show_node(self, node, selected, global_pos):
        self.show_regular(node, selected, global_pos)

    def show_regular(self, node, selected, global_pos):
        super().show_regular(localized_node(node), selected, global_pos)

    def show_mastery(self, node, selected, effect_id, global_pos):
        super().show_mastery(localized_node(node), selected, effect_id, global_pos)
