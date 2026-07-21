"""Zoom-safe passive rendering: node artwork shrinks with tree geometry."""

from __future__ import annotations

from poe1_tree_renderer_v19 import ExplicitProgressionTreeCanvas


class ZoomScaledNodeMixin:
    def _node_size(self, node):
        # Screen-space icons must become genuinely small on an overview.
        # The previous 3.2 px floor turned notables/keystones into overlapping
        # 8-12 px circles while their tree positions were only a few px apart.
        normal = max(1.35, min(15.0, self.scale * 70.0))
        if node.get("isKeystone"):
            return normal * 1.82
        if node.get("isNotable") or node.get("isMastery"):
            return normal * 1.38
        if node.get("classStartIndex") is not None or node.get("isAscendancyStart"):
            return normal * 1.9
        return normal


class ZoomSafeTreeCanvas(ZoomScaledNodeMixin, ExplicitProgressionTreeCanvas):
    pass
