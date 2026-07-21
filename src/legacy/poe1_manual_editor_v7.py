"""Manual editor with reliable combo popups and passive level snapshots."""

from __future__ import annotations

import copy

from PyQt5.QtCore import QEvent, QObject, QTimer, Qt
from PyQt5.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QPushButton, QInputDialog,
)

from poe1_manual_build_v3 import ascendancy_budget, passive_budget
from poe1_manual_build_v4 import (
    SNAPSHOT_KEYS, build_from_state, normalize_passive_stages, state_from_build,
)
from poe1_manual_editor import _button
from poe1_manual_editor_v6 import ManualBuildEditor as PreviousManualBuildEditor


class PopupRaiser(QObject):
    """Keep combo popups above the always-on-top editor on Windows."""

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Show:
            QTimer.singleShot(0, watched.raise_)
            QTimer.singleShot(0, watched.activateWindow)
        return False


class ManualBuildEditor(PreviousManualBuildEditor):
    def __init__(self, overlay, parent=None):
        self._switching_passive_stage = True
        super().__init__(overlay, parent)

        # Reload through the staged model; legacy manual builds are migrated to
        # one snapshot starting at level 1.
        self.state = state_from_build(self.profile.get("build"), self.profile.get("level", 1))
        self.state["passive_stages"] = normalize_passive_stages(self.state)
        self._passive_stage_index = 0
        self._install_passive_stage_controls()
        self._install_combo_popup_fix()
        self._switching_passive_stage = False
        self._populate_passive_stages(0)
        self._load_passive_stage(0, focus=True)

    def _install_combo_popup_fix(self):
        self._popup_raiser = PopupRaiser(self)
        for combo in self.findChildren(QComboBox):
            popup = combo.view().window()
            popup.setWindowFlag(Qt.WindowStaysOnTopHint, True)
            popup.installEventFilter(self._popup_raiser)
            combo.setFocusPolicy(Qt.StrongFocus)

    def _install_passive_stage_controls(self):
        page_layout = self.tree.parentWidget().layout()
        row = QHBoxLayout()
        row.addWidget(QLabel("Этап дерева"))
        self.passive_stage_combo = QComboBox()
        self.passive_stage_combo.setMinimumWidth(220)
        self.passive_stage_combo.currentIndexChanged.connect(self._passive_stage_changed)
        row.addWidget(self.passive_stage_combo, 1)
        add = QPushButton("+ Этап с уровня")
        remove = QPushButton("Удалить этап")
        add.setStyleSheet(_button(True))
        remove.setStyleSheet(_button())
        add.clicked.connect(self._new_passive_stage)
        remove.clicked.connect(self._delete_passive_stage)
        row.addWidget(add)
        row.addWidget(remove)
        page_layout.insertLayout(1, row)

    def _stage_label(self, index):
        stages = self.state["passive_stages"]
        start = int(stages[index]["level"])
        if index + 1 < len(stages):
            end = int(stages[index + 1]["level"]) - 1
            return f"Уровни {start}–{end}"
        return f"С уровня {start} и дальше"

    def _populate_passive_stages(self, selected):
        self.passive_stage_combo.blockSignals(True)
        self.passive_stage_combo.clear()
        for index in range(len(self.state["passive_stages"])):
            self.passive_stage_combo.addItem(self._stage_label(index))
        selected = max(0, min(selected, self.passive_stage_combo.count() - 1))
        self.passive_stage_combo.setCurrentIndex(selected)
        self.passive_stage_combo.blockSignals(False)
        self._passive_stage_index = selected

    def _sync_passive_stage(self):
        if self._switching_passive_stage or not hasattr(self, "passive_stage_combo"):
            return
        stages = self.state.get("passive_stages", [])
        if not (0 <= self._passive_stage_index < len(stages)):
            return
        stage = stages[self._passive_stage_index]
        for key in SNAPSHOT_KEYS:
            default = {} if key == "masteries" else []
            stage[key] = copy.deepcopy(self.state.get(key, default))

    def _load_passive_stage(self, index, focus=False):
        stages = self.state.get("passive_stages", [])
        if not (0 <= index < len(stages)):
            return
        self._switching_passive_stage = True
        self._passive_stage_index = index
        stage = stages[index]
        for key in SNAPSHOT_KEYS:
            default = {} if key == "masteries" else []
            self.state[key] = copy.deepcopy(stage.get(key, default))
        self._switching_passive_stage = False
        super()._refresh_tree(first=focus)
        if focus:
            self._focus_stage_start()

    def _passive_stage_changed(self, index):
        if self._switching_passive_stage or index < 0:
            return
        self._sync_passive_stage()
        self._load_passive_stage(index, focus=True)

    def _new_passive_stage(self):
        self._sync_passive_stage()
        current = self.state["passive_stages"][self._passive_stage_index]
        existing = {int(stage["level"]) for stage in self.state["passive_stages"]}
        suggested = min(100, max(existing) + 12)
        level, ok = QInputDialog.getInt(
            self, "Новый этап дерева", "Действует с уровня:", suggested, 2, 100,
        )
        if not ok:
            return
        if level in existing:
            return self._flash("Этап с этого уровня уже существует")
        stage = copy.deepcopy(current)
        stage["level"] = level
        self.state["passive_stages"].append(stage)
        self.state["passive_stages"].sort(key=lambda item: int(item["level"]))
        index = self.state["passive_stages"].index(stage)
        self._populate_passive_stages(index)
        self._load_passive_stage(index, focus=True)

    def _delete_passive_stage(self):
        stages = self.state["passive_stages"]
        if len(stages) <= 1:
            return self._flash("Должен остаться хотя бы один этап дерева")
        index = self._passive_stage_index
        stages.pop(index)
        index = max(0, index - 1)
        self._populate_passive_stages(index)
        self._load_passive_stage(index, focus=True)

    def _focus_stage_start(self):
        regular = self._selected_regular()
        start = regular[0] if regular else None
        focus = [start] + [str(node) for node in self.state.get("allocation_order", [])[:4]]
        points = [self.tree.positions[node] for node in focus if node in self.tree.positions]
        if not points:
            return
        self.tree.center = points[0]
        self.tree.scale = .16
        self.tree.update()

    def _refresh_tree(self, first=False):
        super()._refresh_tree(first=first)
        self._sync_passive_stage()

    def _save(self):
        self._sync_passive_stage()
        target = self.target_level.value()
        for stage in self.state["passive_stages"]:
            used = len(stage.get("passives", [])) + len(stage.get("masteries", {}))
            if used > passive_budget(target):
                return self._flash("В одном из этапов слишком много пассивов для целевого уровня")
            if len(stage.get("ascendancy_nodes", [])) > ascendancy_budget(target):
                return self._flash("В одном из этапов слишком много очков восхождения")
        live_level = self.profile.get("level", 1)
        self.state["level"] = target
        self.profile["build"] = build_from_state(self.state)
        self.profile["level"] = live_level
        self.overlay.save_profiles()
        self.accept()

