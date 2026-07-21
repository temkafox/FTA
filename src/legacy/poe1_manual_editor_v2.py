"""Manual editor fixes: exact allocation order and stable gem-link editing."""

from __future__ import annotations

import json
from pathlib import Path

from poe1_manual_build_v3 import (
    ascendancy_budget, build_from_state, passive_budget, state_from_build,
)
from poe1_manual_editor import ManualBuildEditor as BaseManualBuildEditor


ROOT = Path(__file__).parent


class ManualBuildEditor(BaseManualBuildEditor):
    def __init__(self, overlay, parent=None):
        super().__init__(overlay, parent)
        loaded = state_from_build(self.profile.get("build"), self.profile.get("level", 1))
        self.state["allocation_order"] = loaded.get("allocation_order", [])
        self.gem_combo.currentTextChanged.connect(self._infer_support)
        self._infer_support(self.gem_combo.currentText())

    def _infer_support(self, name):
        key = (name or "").casefold()
        support = False
        try:
            poedb = json.loads((ROOT / "data" / "poe1" / "poedb_gems_ru.json").read_text(encoding="utf-8"))
            source = (poedb.get(key) or {}).get("source", "")
            support = source.casefold().endswith("_support")
            if not source:
                icons = json.loads((ROOT / "data" / "poe1" / "gem_icons.json").read_text(encoding="utf-8"))
                support = "support" in ((icons.get(key) or {}).get("source", "").casefold())
        except (OSError, ValueError):
            pass
        self.support_check.setChecked(support)

    def _toggle_passive(self, node_id):
        before = node_id in self.state["passives"]
        super()._toggle_passive(node_id)
        after = node_id in self.state["passives"]
        order = self.state.setdefault("allocation_order", [])
        if after and not before and node_id not in order:
            order.append(node_id)
        elif before and not after and node_id in order:
            order.remove(node_id)

    def _toggle_mastery(self, node_id, node):
        before = node_id in self.state["masteries"]
        super()._toggle_mastery(node_id, node)
        after = node_id in self.state["masteries"]
        order = self.state.setdefault("allocation_order", [])
        if after and not before and node_id not in order:
            order.append(node_id)
        elif before and not after and node_id in order:
            order.remove(node_id)

    def _undo_node(self):
        if self.state["ascendancy_nodes"]:
            self.state["ascendancy_nodes"].pop()
        else:
            order = self.state.setdefault("allocation_order", [])
            if order:
                node = order.pop()
                if node in self.state["passives"]:
                    self.state["passives"].remove(node)
                self.state["masteries"].pop(node, None)
        self._refresh_tree()

    def _class_changed(self, class_name):
        old_class = self.state.get("class")
        super()._class_changed(class_name)
        if self.state.get("class") != old_class:
            self.state["allocation_order"] = []

    def _add_gem(self):
        link = self._current_link()
        stage_index = self.stage_combo.currentIndex()
        link_index = self.link_list.currentRow()
        name = self.gem_combo.currentText().strip()
        if not link or not name:
            return self._flash("Сначала создайте и выберите связку")
        link.setdefault("gems", []).append({
            "name": name,
            "support": self.support_check.isChecked(),
            "level": "20",
            "quality": "0",
        })
        self._refresh_stages(stage_index)
        self.link_list.setCurrentRow(link_index)

    def _remove_gem(self):
        link = self._current_link()
        stage_index = self.stage_combo.currentIndex()
        link_index = self.link_list.currentRow()
        gem_index = self.gem_list.currentRow()
        if link and 0 <= gem_index < len(link.get("gems", [])):
            link["gems"].pop(gem_index)
        self._refresh_stages(stage_index)
        self.link_list.setCurrentRow(link_index)

    def _save(self):
        used = len(self.state["passives"]) + len(self.state["masteries"])
        if used > passive_budget(self.target_level.value()):
            return self._flash("Выбрано больше пассивов, чем доступно на этом уровне")
        if len(self.state["ascendancy_nodes"]) > ascendancy_budget(self.target_level.value()):
            return self._flash("Выбрано больше очков восхождения, чем доступно на этом уровне")
        self.state["level"] = self.target_level.value()
        self.profile["level"] = self.target_level.value()
        self.profile["build"] = build_from_state(self.state)
        self.overlay.save_profiles()
        self.accept()
