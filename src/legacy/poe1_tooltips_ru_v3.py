"""Tooltips backed by the official Russian passive-tree payload."""

from poe1_tooltips_ru import RussianGemTooltip
from poe1_tree_renderer_v4 import OpaqueMasteryTooltip
from poe1_ru_text_v2 import localized_node


class OfficialRussianPassiveTooltip(OpaqueMasteryTooltip):
    def show_node(self, node, selected, global_pos):
        self.show_regular(node, selected, global_pos)

    def show_regular(self, node, selected, global_pos):
        super().show_regular(localized_node(node), selected, global_pos)

    def show_mastery(self, node, selected, effect_id, global_pos):
        super().show_mastery(localized_node(node), selected, effect_id, global_pos)
