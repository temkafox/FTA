"""Russian passive tooltip; RussianGemTooltip переехал в actpilot.gems.widgets."""

from __future__ import annotations

from actpilot.ru_text import localized_node
from actpilot.tree import OpaqueMasteryTooltip


class RussianPassiveTooltip(OpaqueMasteryTooltip):
    def show_node(self, node, selected, global_pos):
        self.show_regular(node, selected, global_pos)

    def show_regular(self, node, selected, global_pos):
        super().show_regular(localized_node(node), selected, global_pos)

    def show_mastery(self, node, selected, effect_id, global_pos):
        super().show_mastery(localized_node(node), selected, effect_id, global_pos)
