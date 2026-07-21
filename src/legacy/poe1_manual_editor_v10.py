"""Manual editor with explicit level ranges for gem-link stages."""

from __future__ import annotations

import copy

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QPushButton

from poe1_manual_editor import _button
from poe1_manual_editor_v8 import ChoiceDialog
from poe1_manual_editor_v9 import ManualBuildEditor as PreviousManualBuildEditor


class ManualBuildEditor(PreviousManualBuildEditor):
    def __init__(self, overlay, parent=None):
        self._gem_stage_switching = True
        super().__init__(overlay, parent)
        self._install_gem_stage_controls()
        self._gem_stage_switching = False
        self._sync_gem_stage_button()

    def _sorted_gem_stages(self):
        stages = self.state.setdefault("gem_stages", [])
        stages.sort(key=lambda stage: int(stage.get("level", 1)))
        return stages

    def _gem_stage_label(self, index):
        stages = self._sorted_gem_stages()
        if not (0 <= index < len(stages)):
            return "Этапов пока нет"
        start = int(stages[index].get("level", 1))
        if index + 1 < len(stages):
            end = int(stages[index + 1].get("level", 1)) - 1
            return f"Уровни {start}–{end}"
        return f"С уровня {start} и дальше"

    def _install_gem_stage_controls(self):
        page = self.gem_level_picker.parentWidget()
        page_layout = page.layout()

        # Remove the old level-centric wording. The hidden spin box remains as
        # the compatibility value used by inherited editing helpers.
        self.gem_level_picker.hide()
        self.gem_level_picker.setMaximumWidth(0)
        self.gem_version_label.hide()
        self.gem_version_label.setMaximumWidth(0)
        for label in page.findChildren(QLabel, options=Qt.FindDirectChildrenOnly):
            if label.text() == "Камни на уровне":
                label.hide()
                label.setMaximumWidth(0)
        for button in page.findChildren(QPushButton, options=Qt.FindDirectChildrenOnly):
            if button.text() == "Вернуть предыдущий набор":
                button.hide()
                button.setMaximumWidth(0)

        row = QHBoxLayout()
        row.addWidget(QLabel("Этап камней"))
        self.gem_stage_button = QPushButton()
        self.gem_stage_button.setStyleSheet(_button())
        self.gem_stage_button.setCursor(Qt.PointingHandCursor)
        self.gem_stage_button.clicked.connect(self._choose_gem_stage)
        row.addWidget(self.gem_stage_button, 1)
        add = QPushButton("+ Этап")
        remove = QPushButton("Удалить")
        add.setStyleSheet(_button(True))
        remove.setStyleSheet(_button())
        add.clicked.connect(self._new_gem_stage)
        remove.clicked.connect(self._delete_gem_stage)
        row.addWidget(add)
        row.addWidget(remove)
        page_layout.insertLayout(1, row)

    def _current_gem_stage_index(self):
        stages = self._sorted_gem_stages()
        if not stages:
            return -1
        level = self.gem_level_picker.value()
        eligible = [
            index for index, stage in enumerate(stages)
            if int(stage.get("level", 1)) <= level
        ]
        return eligible[-1] if eligible else 0

    def _sync_gem_stage_button(self):
        if not hasattr(self, "gem_stage_button"):
            return
        self.gem_stage_button.setText(
            self._gem_stage_label(self._current_gem_stage_index())
        )

    def _select_gem_stage(self, index):
        stages = self._sorted_gem_stages()
        if not (0 <= index < len(stages)):
            return
        self._gem_stage_switching = True
        self.gem_level_picker.setValue(int(stages[index].get("level", 1)))
        self._gem_stage_switching = False
        self._show_gems_for_level(self.gem_level_picker.value())
        self._sync_gem_stage_button()

    def _choose_gem_stage(self):
        stages = self._sorted_gem_stages()
        if not stages:
            return self._new_gem_stage()
        labels = [self._gem_stage_label(index) for index in range(len(stages))]
        current_index = self._current_gem_stage_index()
        selected = ChoiceDialog.choose(
            "Выберите этап камней", labels, labels[current_index], self,
        )
        if selected in labels:
            self._select_gem_stage(labels.index(selected))

    def _new_gem_stage(self):
        stages = self._sorted_gem_stages()
        existing = {int(stage.get("level", 1)) for stage in stages}
        current_index = self._current_gem_stage_index()
        suggested = min(100, max(existing or {0}) + 12)
        selected = ChoiceDialog.choose(
            "Новый этап камней",
            [str(level) for level in range(1, 101) if level not in existing],
            str(suggested),
            self,
        )
        if not selected:
            return
        level = int(selected)
        inherited = stages[current_index] if 0 <= current_index < len(stages) else None
        stage = {
            "level": level,
            "title": f"Камни с уровня {level}",
            "links": copy.deepcopy(inherited.get("links", [])) if inherited else [],
        }
        stages.append(stage)
        stages.sort(key=lambda item: int(item.get("level", 1)))
        self._select_gem_stage(stages.index(stage))

    def _delete_gem_stage(self):
        stages = self._sorted_gem_stages()
        if len(stages) <= 1:
            return self._flash("Должен остаться хотя бы один этап камней")
        index = self._current_gem_stage_index()
        if not (0 <= index < len(stages)):
            return
        stages.pop(index)
        self._select_gem_stage(max(0, index - 1))

    def _show_gems_for_level(self, level, preferred_link=0):
        super()._show_gems_for_level(level, preferred_link)
        if not getattr(self, "_gem_stage_switching", False):
            self._sync_gem_stage_button()

