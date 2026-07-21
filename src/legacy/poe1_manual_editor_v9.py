"""Manual editor camera that never aliases or mutates a node position."""

from __future__ import annotations

from PyQt5.QtCore import QPointF

import poe1_manual_editor_v5 as canvas_module
from poe1_manual_editor_v5 import ZoomSafeManualTreeCanvas
from poe1_manual_editor_v8 import ManualBuildEditor as PreviousManualBuildEditor


class SafePanManualTreeCanvas(ZoomSafeManualTreeCanvas):
    def mousePressEvent(self, event):
        # QPointF wrappers are mutable. Never let camera centre share the same
        # object as an entry in self.positions.
        self.center = QPointF(self.center.x(), self.center.y())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_start is None:
            return super().mouseMoveEvent(event)
        self.node_tooltip.hide()
        delta = event.pos() - self._drag_start
        self._drag_start = event.pos()
        # Assignment creates a fresh point. The old `self.center -= ...` could
        # mutate a node position when centre was assigned from positions[id].
        self.center = QPointF(
            self.center.x() - delta.x() / self.scale,
            self.center.y() - delta.y() / self.scale,
        )
        self.update()


# poe1_manual_editor_v5 resolves this module global when constructing the
# canvas, so all newer editor subclasses receive the safe implementation.
canvas_module.ZoomSafeManualTreeCanvas = SafePanManualTreeCanvas


class ManualBuildEditor(PreviousManualBuildEditor):
    def _focus_stage_start(self):
        regular = self._selected_regular()
        start = regular[0] if regular else None
        point = self.tree.positions.get(start) if start else None
        if point is None:
            return
        self.tree.center = QPointF(point.x(), point.y())
        self.tree.scale = .16
        self.tree.update()

