"""Gem editor with every level range and its links visible at once."""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView, QLabel, QListWidget, QTreeWidget, QTreeWidgetItem,
)

from poe1_manual_editor_v10 import ManualBuildEditor as PreviousManualBuildEditor


class ManualBuildEditor(PreviousManualBuildEditor):
    def __init__(self, overlay, parent=None):
        self._overview_syncing = True
        super().__init__(overlay, parent)
        self._install_gem_stage_overview()
        self._overview_syncing = False
        self._rebuild_gem_stage_overview()

    def _install_gem_stage_overview(self):
        page = self.gem_level_picker.parentWidget()

        # Remove every remnant of the old arbitrary-level workflow, including
        # the explanatory paragraph and inherited-version status text.
        self.gem_level_picker.hide()
        self.gem_level_picker.setMaximumSize(0, 0)
        self.gem_version_label.hide()
        self.gem_version_label.setMaximumSize(0, 0)
        self.gem_stage_button.hide()
        self.gem_stage_button.setMaximumSize(0, 0)
        for label in page.findChildren(QLabel):
            text = label.text().strip()
            if (
                text.startswith("Выберите уровень персонажа")
                or text in {"Камни на уровне", "Этап камней"}
            ):
                label.hide()
                label.setMaximumSize(0, 0)
            elif text == "Связки":
                label.setText("Этапы и связки")
        for button in page.findChildren(QListWidget):
            if button is self.link_list:
                continue

        parent = self.link_list.parentWidget()
        layout = parent.layout()
        index = layout.indexOf(self.link_list)
        self.link_list.hide()
        self.link_list.setMaximumSize(0, 0)

        self.gem_stage_tree = QTreeWidget(parent)
        self.gem_stage_tree.setHeaderHidden(True)
        self.gem_stage_tree.setRootIsDecorated(False)
        self.gem_stage_tree.setIndentation(16)
        self.gem_stage_tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self.gem_stage_tree.setUniformRowHeights(True)
        self.gem_stage_tree.setStyleSheet("""
            QTreeWidget { border: 1px solid #4f3c1c; background: rgba(5,7,7,.52); }
            QTreeWidget::item { padding: 4px 6px; color: #ded7c8; }
            QTreeWidget::item:selected { background: #173d2b; color: white; }
        """)
        self.gem_stage_tree.currentItemChanged.connect(self._gem_overview_changed)
        layout.insertWidget(index, self.gem_stage_tree, 1)

    def _range_title(self, index):
        stages = self._sorted_gem_stages()
        if not (0 <= index < len(stages)):
            return "Этапов пока нет"
        start = int(stages[index].get("level", 1))
        if index + 1 < len(stages):
            end = int(stages[index + 1].get("level", 1)) - 1
            return f"УРОВНИ {start}–{end}"
        return f"С УРОВНЯ {start} И ДАЛЬШЕ"

    @staticmethod
    def _link_title(link):
        names = [
            (gem.get("name") or "").strip()
            for gem in link.get("gems", [])
            if (gem.get("name") or "").strip()
        ]
        return " — ".join(names) or "Пустая связка"

    def _rebuild_gem_stage_overview(self, selected_stage=None, selected_link=None):
        if not hasattr(self, "gem_stage_tree") or self._overview_syncing:
            return
        stages = self._sorted_gem_stages()
        if selected_stage is None:
            selected_stage = self._current_gem_stage_index()
        if selected_link is None:
            selected_link = self.link_list.currentRow()
        self._overview_syncing = True
        self.gem_stage_tree.clear()
        wanted = None
        for stage_index, stage in enumerate(stages):
            header = QTreeWidgetItem([self._range_title(stage_index)])
            header.setData(0, Qt.UserRole, (stage_index, -1))
            font = header.font(0)
            font.setBold(True)
            header.setFont(0, font)
            header.setForeground(0, Qt.yellow)
            self.gem_stage_tree.addTopLevelItem(header)
            links = stage.get("links", [])
            if not links:
                empty = QTreeWidgetItem(["Пустой этап"])
                empty.setData(0, Qt.UserRole, (stage_index, -1))
                header.addChild(empty)
                if stage_index == selected_stage:
                    wanted = header
            for link_index, link in enumerate(links):
                child = QTreeWidgetItem([self._link_title(link)])
                child.setData(0, Qt.UserRole, (stage_index, link_index))
                header.addChild(child)
                if stage_index == selected_stage and link_index == selected_link:
                    wanted = child
            if stage_index == selected_stage and wanted is None:
                wanted = header
            header.setExpanded(True)
        if wanted is not None:
            self.gem_stage_tree.setCurrentItem(wanted)
            self.gem_stage_tree.scrollToItem(wanted)
        self._overview_syncing = False

    def _gem_overview_changed(self, current, previous):
        if self._overview_syncing or current is None:
            return
        data = current.data(0, Qt.UserRole)
        if not data:
            return
        stage_index, link_index = data
        stages = self._sorted_gem_stages()
        if not (0 <= stage_index < len(stages)):
            return
        self._overview_syncing = True
        self.gem_level_picker.blockSignals(True)
        self.gem_level_picker.setValue(int(stages[stage_index].get("level", 1)))
        self.gem_level_picker.blockSignals(False)
        self._show_gems_for_level(
            self.gem_level_picker.value(), max(0, int(link_index)),
        )
        self._overview_syncing = False
        self._rebuild_gem_stage_overview(stage_index, int(link_index))

    def _show_gems_for_level(self, level, preferred_link=0):
        super()._show_gems_for_level(level, preferred_link)
        if hasattr(self, "gem_stage_tree") and not self._overview_syncing:
            self._rebuild_gem_stage_overview(
                self._current_gem_stage_index(), self.link_list.currentRow(),
            )

    def _select_gem_stage(self, index):
        super()._select_gem_stage(index)
        if hasattr(self, "gem_stage_tree"):
            self._rebuild_gem_stage_overview(index, 0)

