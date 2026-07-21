"""Manual editor with non-popup selectors and deterministic start-node focus."""

from __future__ import annotations

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import (
    QDialog, QDialogButtonBox, QLabel, QListWidget, QPushButton, QVBoxLayout,
)

import main as legacy
from poe1_manual_build import CLASS_START_INDEX
from poe1_manual_editor import _button
from poe1_manual_editor_v7 import ManualBuildEditor as PreviousManualBuildEditor


class ChoiceDialog(QDialog):
    """Real modal window, avoiding unreliable QComboBox popups over PoE."""

    def __init__(self, title, values, current, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.Dialog | Qt.WindowStaysOnTopHint)
        self.setModal(True)
        self.resize(360, min(560, 100 + max(4, len(values)) * 32))
        layout = QVBoxLayout(self)
        self.list = QListWidget()
        self.list.addItems([str(value) for value in values])
        matches = self.list.findItems(str(current), Qt.MatchExactly)
        if matches:
            self.list.setCurrentItem(matches[0])
            self.list.scrollToItem(matches[0])
        self.list.itemDoubleClicked.connect(lambda _: self.accept())
        layout.addWidget(self.list, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @classmethod
    def choose(cls, title, values, current, parent=None):
        dialog = cls(title, values, current, parent)
        legacy.set_window_click_through(dialog, False)
        if dialog.exec_() != QDialog.Accepted or not dialog.list.currentItem():
            return None
        return dialog.list.currentItem().text()


class ManualBuildEditor(PreviousManualBuildEditor):
    def __init__(self, overlay, parent=None):
        super().__init__(overlay, parent)
        self._install_reliable_selectors()
        self._force_editor_input()
        self._sync_selector_texts()

    def _force_editor_input(self):
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setWindowFlag(Qt.WindowTransparentForInput, False)
        legacy.set_window_click_through(self, False)
        self.setEnabled(True)
        for widget in (self.tree, self.class_button, self.asc_button,
                       self.level_button, self.passive_stage_button):
            widget.setAttribute(Qt.WA_TransparentForMouseEvents, False)
            widget.setEnabled(True)

    @staticmethod
    def _replace_in_layout(layout, old_widget, new_widget):
        index = layout.indexOf(old_widget)
        if index < 0:
            return
        layout.removeWidget(old_widget)
        old_widget.hide()
        old_widget.setMaximumSize(0, 0)
        layout.insertWidget(index, new_widget)

    def _selector_button(self, slot):
        button = QPushButton()
        button.setStyleSheet(_button())
        button.setCursor(Qt.PointingHandCursor)
        button.clicked.connect(slot)
        return button

    def _install_reliable_selectors(self):
        controls = self.tree.parentWidget().layout().itemAt(0).layout()
        self.class_button = self._selector_button(self._choose_class)
        self.asc_button = self._selector_button(self._choose_ascendancy)
        self.level_button = self._selector_button(self._choose_target_level)
        self._replace_in_layout(controls, self.class_combo, self.class_button)
        self._replace_in_layout(controls, self.asc_combo, self.asc_button)
        self._replace_in_layout(controls, self.target_level, self.level_button)

        stage_row = self.tree.parentWidget().layout().itemAt(1).layout()
        self.passive_stage_button = self._selector_button(self._choose_passive_stage)
        self._replace_in_layout(
            stage_row, self.passive_stage_combo, self.passive_stage_button,
        )

    def _choose_class(self):
        value = ChoiceDialog.choose(
            "Выберите класс", list(CLASS_START_INDEX), self.class_combo.currentText(), self,
        )
        if value:
            self.class_combo.setCurrentText(value)
            self._sync_selector_texts()
            QTimer.singleShot(0, self._focus_stage_start)

    def _choose_ascendancy(self):
        values = [self.asc_combo.itemText(i) for i in range(self.asc_combo.count())]
        value = ChoiceDialog.choose(
            "Выберите восхождение", values, self.asc_combo.currentText(), self,
        )
        if value:
            self.asc_combo.setCurrentText(value)
            self._sync_selector_texts()

    def _choose_target_level(self):
        value = ChoiceDialog.choose(
            "Целевой уровень плана",
            [str(level) for level in range(1, 101)],
            str(self.target_level.value()), self,
        )
        if value:
            self.target_level.setValue(int(value))
            self._sync_selector_texts()

    def _choose_passive_stage(self):
        labels = [self._stage_label(i) for i in range(len(self.state["passive_stages"]))]
        current = self._stage_label(self._passive_stage_index)
        value = ChoiceDialog.choose("Выберите этап дерева", labels, current, self)
        if value in labels:
            index = labels.index(value)
            self.passive_stage_combo.setCurrentIndex(index)
            self._sync_selector_texts()

    def _sync_selector_texts(self):
        if not hasattr(self, "class_button"):
            return
        self.class_button.setText(self.class_combo.currentText())
        self.asc_button.setText(self.asc_combo.currentText())
        self.level_button.setText(str(self.target_level.value()))
        stages = self.state.get("passive_stages", [])
        if stages:
            self.passive_stage_button.setText(self._stage_label(self._passive_stage_index))

    def _populate_passive_stages(self, selected):
        super()._populate_passive_stages(selected)
        self._sync_selector_texts()

    def _load_passive_stage(self, index, focus=False):
        super()._load_passive_stage(index, focus=focus)
        self._sync_selector_texts()

    def _class_changed(self, class_name):
        super()._class_changed(class_name)
        self._sync_selector_texts()
        QTimer.singleShot(0, self._focus_stage_start)

    def _ascendancy_changed(self, name):
        super()._ascendancy_changed(name)
        self._sync_selector_texts()

    def _level_changed(self, value):
        super()._level_changed(value)
        self._sync_selector_texts()

    def showEvent(self, event):
        self._force_editor_input()
        super().showEvent(event)
        # Layout and DPI geometry are final only after the native window is
        # shown. Centre then, so a later resize cannot move WITCH to an edge.
        QTimer.singleShot(0, self._focus_stage_start)

