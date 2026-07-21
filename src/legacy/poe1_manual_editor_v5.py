"""Simplified level-centric gem editor and zoom-safe manual tree."""

from __future__ import annotations

import copy

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPainter, QPen
from PyQt5.QtWidgets import (
    QCheckBox, QComboBox, QHBoxLayout, QLabel, QListWidget, QPushButton,
    QSpinBox, QSplitter, QVBoxLayout, QWidget,
)

from poe1_manual_editor import _button
from poe1_manual_editor_v4 import (
    ManualBuildEditor as PreviousManualBuildEditor, StableManualTreeCanvas,
)
from poe1_tree_renderer_v20 import ZoomScaledNodeMixin


class ZoomSafeManualTreeCanvas(ZoomScaledNodeMixin, StableManualTreeCanvas):
    def paintEvent(self, event):
        available = self.available_nodes
        self.available_nodes = set()
        super().paintEvent(event)
        self.available_nodes = available
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor("#d8b759"), max(.7, min(1.2, self.scale * 12))))
        for node_id in available:
            point = self.positions.get(node_id)
            if point is None:
                continue
            screen = self._screen(point)
            if not self.rect().contains(screen.toPoint()):
                continue
            size = self._node_size(self.nodes.get(node_id, {}))
            radius = size / 2 + max(1.0, size * .18)
            painter.drawEllipse(screen, radius, radius)
        painter.end()


class ManualBuildEditor(PreviousManualBuildEditor):
    def __init__(self, overlay, parent=None):
        super().__init__(overlay, parent)
        old_tree = self.tree
        layout = old_tree.parentWidget().layout()
        index = layout.indexOf(old_tree)
        layout.removeWidget(old_tree)
        old_tree.deleteLater()
        self.tree = ZoomSafeManualTreeCanvas()
        self.tree.node_clicked.connect(self._node_clicked)
        layout.insertWidget(index, self.tree, 1)
        self._active_stage_index = -1
        self._refresh_tree(first=True)
        self._refresh_stages()

    def _gem_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        explanation = QLabel(
            "Выберите уровень персонажа. Ниже показаны связки, которые будут использоваться на этом уровне. "
            "Любое изменение автоматически создаёт новую версию связок с выбранного уровня."
        )
        explanation.setWordWrap(True)
        explanation.setStyleSheet("color:#b7ad96; padding:3px 0 7px 0;")
        layout.addWidget(explanation)

        level_row = QHBoxLayout()
        level_row.addWidget(QLabel("Камни на уровне"))
        self.gem_level_picker = QSpinBox()
        self.gem_level_picker.setRange(1, 100)
        self.gem_level_picker.valueChanged.connect(self._gem_level_changed)
        level_row.addWidget(self.gem_level_picker)
        self.gem_version_label = QLabel()
        self.gem_version_label.setStyleSheet("color:#d5bb7b;")
        level_row.addWidget(self.gem_version_label, 1)
        revert = QPushButton("Вернуть предыдущий набор")
        revert.setStyleSheet(_button())
        revert.clicked.connect(self._revert_level_gems)
        level_row.addWidget(revert)
        layout.addLayout(level_row)

        # Kept as hidden compatibility controls for inherited save helpers.
        self.stage_combo = QComboBox()
        self.stage_combo.hide()
        self.stage_level = QSpinBox()
        self.stage_level.hide()

        splitter = QSplitter(Qt.Horizontal)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 5, 0)
        left_layout.addWidget(QLabel("Связки"))
        self.link_list = QListWidget()
        self.link_list.currentRowChanged.connect(self._link_changed)
        left_layout.addWidget(self.link_list, 1)
        link_row = QHBoxLayout()
        add_link = QPushButton("+ Новая связка")
        remove_link = QPushButton("Удалить связку")
        add_link.setStyleSheet(_button(True))
        remove_link.setStyleSheet(_button())
        add_link.clicked.connect(self._new_link)
        remove_link.clicked.connect(self._delete_link)
        link_row.addWidget(add_link)
        link_row.addWidget(remove_link)
        left_layout.addLayout(link_row)
        splitter.addWidget(left)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(5, 0, 0, 0)
        right_layout.addWidget(QLabel("Камни выбранной связки"))
        self.gem_list = QListWidget()
        right_layout.addWidget(self.gem_list, 1)
        picker = QHBoxLayout()
        self.gem_combo = QComboBox()
        self.gem_combo.setEditable(True)
        import json
        from pathlib import Path
        catalog = json.loads((Path(__file__).parent / "data" / "poe1" / "gem_catalog.json").read_text(encoding="utf-8"))
        self.gem_combo.addItems(sorted(item.get("name", key) for key, item in catalog.items()))
        self.support_check = QCheckBox("камень поддержки")
        add_gem = QPushButton("Добавить камень")
        remove_gem = QPushButton("Удалить")
        add_gem.setStyleSheet(_button(True))
        remove_gem.setStyleSheet(_button())
        add_gem.clicked.connect(self._add_gem)
        remove_gem.clicked.connect(self._remove_gem)
        picker.addWidget(self.gem_combo, 1)
        picker.addWidget(self.support_check)
        picker.addWidget(add_gem)
        picker.addWidget(remove_gem)
        right_layout.addLayout(picker)
        splitter.addWidget(right)
        splitter.setSizes([380, 650])
        layout.addWidget(splitter, 1)
        return page

    def _effective_stage_index(self, level):
        stages = self.state.get("gem_stages", [])
        eligible = [
            (int(stage.get("level", 1)), index)
            for index, stage in enumerate(stages) if int(stage.get("level", 1)) <= level
        ]
        if eligible:
            return max(eligible)[1]
        return -1

    def _exact_stage_index(self, level):
        return next(
            (index for index, stage in enumerate(self.state.get("gem_stages", []))
             if int(stage.get("level", 1)) == level),
            -1,
        )

    def _refresh_stages(self, selected=0):
        if not hasattr(self, "gem_level_picker"):
            return
        level = self.gem_level_picker.value() or int(self.state.get("level", 1))
        self._show_gems_for_level(level)

    def _gem_level_changed(self, level):
        if getattr(self, "_loading", False):
            return
        self._show_gems_for_level(level)

    def _show_gems_for_level(self, level, preferred_link=0):
        self._active_stage_index = self._effective_stage_index(level)
        stage = self._current_stage()
        exact = self._exact_stage_index(level)
        if exact >= 0:
            self.gem_version_label.setText(f"Свои изменения действуют с уровня {level}")
        elif stage:
            self.gem_version_label.setText(f"Наследуется набор с уровня {stage.get('level', 1)}")
        else:
            self.gem_version_label.setText("Связок пока нет")
        self.link_list.clear()
        for number, link in enumerate(stage.get("links", []) if stage else [], 1):
            names = " — ".join(gem.get("name", "") for gem in link.get("gems", []))
            self.link_list.addItem(f"Связка {number}: {names or 'пусто'}")
        if self.link_list.count():
            self.link_list.setCurrentRow(max(0, min(preferred_link, self.link_list.count() - 1)))
        else:
            self.gem_list.clear()

    def _current_stage(self):
        stages = self.state.get("gem_stages", [])
        return stages[self._active_stage_index] if 0 <= self._active_stage_index < len(stages) else None

    def _ensure_editable_stage(self):
        level = self.gem_level_picker.value()
        exact = self._exact_stage_index(level)
        if exact >= 0:
            self._active_stage_index = exact
            return self.state["gem_stages"][exact]
        inherited = self._current_stage()
        stage = {
            "level": level,
            "title": f"Камни с уровня {level}",
            "links": copy.deepcopy(inherited.get("links", [])) if inherited else [],
        }
        self.state["gem_stages"].append(stage)
        self.state["gem_stages"].sort(key=lambda item: int(item.get("level", 1)))
        self._active_stage_index = self.state["gem_stages"].index(stage)
        return stage

    def _current_link(self):
        stage = self._current_stage()
        row = self.link_list.currentRow()
        links = stage.get("links", []) if stage else []
        return links[row] if 0 <= row < len(links) else None

    def _new_link(self):
        stage = self._ensure_editable_stage()
        stage.setdefault("links", []).append({"label": f"Связка {len(stage['links']) + 1}", "gems": []})
        self._show_gems_for_level(self.gem_level_picker.value(), len(stage["links"]) - 1)

    def _delete_link(self):
        row = self.link_list.currentRow()
        stage = self._ensure_editable_stage()
        if 0 <= row < len(stage.get("links", [])):
            stage["links"].pop(row)
        self._show_gems_for_level(self.gem_level_picker.value(), max(0, row - 1))

    def _add_gem(self):
        row = self.link_list.currentRow()
        stage = self._ensure_editable_stage()
        if row < 0:
            stage.setdefault("links", []).append({"label": "Связка 1", "gems": []})
            row = len(stage["links"]) - 1
        name = self.gem_combo.currentText().strip()
        if not name:
            return
        stage["links"][row].setdefault("gems", []).append({
            "name": name, "support": self.support_check.isChecked(),
            "level": "20", "quality": "0",
        })
        self._show_gems_for_level(self.gem_level_picker.value(), row)

    def _remove_gem(self):
        link_row = self.link_list.currentRow()
        gem_row = self.gem_list.currentRow()
        stage = self._ensure_editable_stage()
        if 0 <= link_row < len(stage.get("links", [])):
            gems = stage["links"][link_row].get("gems", [])
            if 0 <= gem_row < len(gems):
                gems.pop(gem_row)
        self._show_gems_for_level(self.gem_level_picker.value(), max(0, link_row))

    def _link_changed(self, row):
        self.gem_list.clear()
        link = self._current_link()
        if not link:
            return
        for gem in link.get("gems", []):
            suffix = " · поддержка" if gem.get("support") else ""
            self.gem_list.addItem(gem.get("name", "") + suffix)

    def _revert_level_gems(self):
        level = self.gem_level_picker.value()
        exact = self._exact_stage_index(level)
        if exact >= 0:
            self.state["gem_stages"].pop(exact)
        self._show_gems_for_level(level)

    def _load_state_to_controls(self):
        super()._load_state_to_controls()
        if hasattr(self, "gem_level_picker"):
            self.gem_level_picker.blockSignals(True)
            self.gem_level_picker.setValue(int(self.state.get("level", self.profile.get("level", 1))))
            self.gem_level_picker.blockSignals(False)
            self._show_gems_for_level(self.gem_level_picker.value())
