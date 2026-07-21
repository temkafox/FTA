"""Manual editor with signal-safe loading of an existing build."""

from __future__ import annotations

from poe1_manual_editor_v2 import ManualBuildEditor as PreviousManualBuildEditor


class ManualBuildEditor(PreviousManualBuildEditor):
    def _load_state_to_controls(self):
        was_loading = self._loading
        self._loading = True
        self.class_combo.setCurrentText(self.state.get("class", "Witch"))
        self._fill_ascendancies(self.state.get("ascendancy"))
        self.target_level.setValue(int(self.state.get("level", self.profile.get("level", 1))))
        self._loading = was_loading
        self._refresh_tree(first=True)
        self._refresh_stages()
