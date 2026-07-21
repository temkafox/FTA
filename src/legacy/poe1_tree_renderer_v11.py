"""Quest-aware tree renderer without level badges on passive nodes."""

from poe1_tree_renderer_v9 import ImmediateFocusTreeCanvas
from poe1_tree_renderer_v10 import QuestAwareTreeCanvas


class CleanPassiveTreeCanvas(QuestAwareTreeCanvas):
    def _draw_route_node(self, painter, node_id):
        # Skip QuestAwareTreeCanvas' marker overlay. Its parent still renders
        # the correct green/gold state and immediate-focus ring.
        ImmediateFocusTreeCanvas._draw_route_node(self, painter, node_id)
