"""Russian tooltip bodies with original English passive and gem names."""

from __future__ import annotations

import html

from poe1_gem_widgets_v4 import CleanGemDetailTooltip
from poe1_ru_text import gem_description, localized_node
from poe1_tree_renderer_v4 import OpaqueMasteryTooltip


class RussianPassiveTooltip(OpaqueMasteryTooltip):
    def show_node(self, node, selected, global_pos):
        self.show_regular(node, selected, global_pos)

    def show_regular(self, node, selected, global_pos):
        super().show_regular(localized_node(node), selected, global_pos)

    def show_mastery(self, node, selected, effect_id, global_pos):
        super().show_mastery(localized_node(node), selected, effect_id, global_pos)


class RussianGemTooltip(CleanGemDetailTooltip):
    def show_gem(self, gem, global_pos):
        super().show_gem(gem, global_pos)
        description = gem_description(gem.get("name"))
        if not description:
            description = "Русское описание этого камня пока отсутствует в локальных данных."
        self.description.setText(html.escape(description).replace("\n", "<br>"))
        self.details.clear()
        self.details.hide()
        self.adjustSize()
