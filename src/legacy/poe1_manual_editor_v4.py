"""Stable-camera manual editor with strict last-allocation undo rules."""

from __future__ import annotations

from poe1_manual_editor import ManualTreeCanvas
from poe1_manual_editor_v3 import ManualBuildEditor as PreviousManualBuildEditor


class StableManualTreeCanvas(ManualTreeCanvas):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._editor_initialized = False

    def set_editor_state(self, regular, masteries, ascendancy_name, ascendancy_nodes):
        old_center, old_scale = self.center, self.scale
        super().set_editor_state(regular, masteries, ascendancy_name, ascendancy_nodes)
        if self._editor_initialized:
            self.center, self.scale = old_center, old_scale
            self.update()
        else:
            self._editor_initialized = True


class ManualBuildEditor(PreviousManualBuildEditor):
    def __init__(self, overlay, parent=None):
        super().__init__(overlay, parent)
        old_tree = self.tree
        layout = old_tree.parentWidget().layout()
        index = layout.indexOf(old_tree)
        layout.removeWidget(old_tree)
        old_tree.deleteLater()
        self.tree = StableManualTreeCanvas()
        self.tree.node_clicked.connect(self._node_clicked)
        layout.insertWidget(index, self.tree, 1)
        self._refresh_tree(first=True)

    def _toggle_passive(self, node_id):
        if node_id in self.state["passives"]:
            order = self.state.setdefault("allocation_order", [])
            if not order or order[-1] != node_id:
                return self._flash("Отменить можно только последнее потраченное очко")
        super()._toggle_passive(node_id)

    def _toggle_mastery(self, node_id, node):
        if node_id in self.state["masteries"]:
            order = self.state.setdefault("allocation_order", [])
            if not order or order[-1] != node_id:
                return self._flash("Отменить можно только последнее потраченное очко")
        super()._toggle_mastery(node_id, node)
