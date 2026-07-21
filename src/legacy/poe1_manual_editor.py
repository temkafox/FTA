"""Interactive PoE 1 passive-tree and gem-stage editor for ActPilot."""

from __future__ import annotations

import copy
import json
import math
from pathlib import Path

from PyQt5.QtCore import QPoint, Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QPainter, QPen
from PyQt5.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QHBoxLayout, QLabel, QInputDialog,
    QListWidget, QMessageBox, QPushButton, QSpinBox, QSplitter, QTabWidget,
    QVBoxLayout, QWidget,
)

import main as legacy
from poe1_manual_build_v2 import (
    ASCENDANCIES, CLASS_START_INDEX, ascendancy_budget, ascendancy_start_id,
    build_from_state, class_start_id, load_tree, passive_budget, state_from_build,
)
from poe1_ru_text import localized_node
from poe1_tree_renderer_v19 import ExplicitProgressionTreeCanvas


ROOT = Path(__file__).parent


def _button(primary=False):
    color = legacy.Style.ACCENT if primary else "rgba(8,9,9,190)"
    text = legacy.Style.BG if primary else legacy.Style.TEXT_SECONDARY
    return f"""
        QPushButton {{background:{color}; color:{text}; border:1px solid rgba(154,116,57,.42);
            border-radius:{legacy.Style.RAD_S}px; padding:5px 10px;}}
        QPushButton:hover {{border-color:#d0aa61; color:{legacy.Style.TEXT_PRIMARY};}}
    """


class ManualTreeCanvas(ExplicitProgressionTreeCanvas):
    node_clicked = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._click_origin = None
        self.available_nodes = set()

    def set_editor_state(self, regular, masteries, ascendancy_name, ascendancy_nodes):
        regular = [str(node) for node in regular]
        mastery_ids = {str(node) for node in masteries}
        self.set_quest_progression(regular, regular, [], {}, {})
        self.set_mastery_progression(mastery_ids)
        self.selected_masteries = {
            str(node): int(effect) for node, effect in masteries.items() if effect
        }
        asc = [str(node) for node in ascendancy_nodes if str(node) in self.positions]
        self.ascendancy = {
            "name": ascendancy_name,
            "nodes": asc,
            "edges": sorted(self._explicit_edges(asc)),
            "completed": asc,
            "next": [],
        }
        self.update()

    def set_available(self, nodes):
        self.available_nodes = {str(node) for node in nodes}
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._click_origin = QPoint(event.pos())
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        clicked = None
        if event.button() == Qt.LeftButton and self._click_origin is not None:
            if (event.pos() - self._click_origin).manhattanLength() <= 5:
                clicked = self._node_at(event)
        self._click_origin = None
        super().mouseReleaseEvent(event)
        if clicked:
            self.node_clicked.emit(clicked)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor("#d8b759"), 1.2))
        for node_id in self.available_nodes:
            point = self.positions.get(node_id)
            if point is None:
                continue
            screen = self._screen(point)
            if not self.rect().contains(screen.toPoint()):
                continue
            radius = max(5.5, self._node_size(self.nodes.get(node_id, {})) / 2 + 4)
            painter.drawEllipse(screen, radius, radius)
        painter.end()


class ManualBuildEditor(QDialog):
    def __init__(self, overlay, parent=None):
        super().__init__(parent or overlay)
        self.overlay = overlay
        self.profile = overlay.active_profile()
        self.tree_data = load_tree()
        self.nodes = self.tree_data.get("nodes", {})
        self.state = state_from_build(self.profile.get("build"), self.profile.get("level", 1))
        self.state.setdefault("masteries", {})
        self.state.setdefault("passives", [])
        self.state.setdefault("ascendancy_nodes", [])
        self.state.setdefault("gem_stages", [])
        self._loading = True

        self.setWindowTitle("ActPilot — ручной редактор PoE 1")
        self.setWindowFlags(Qt.Dialog | Qt.WindowStaysOnTopHint)
        self.resize(1180, 760)
        self.setMinimumSize(940, 620)
        self.setStyleSheet(self._style())
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        title = QLabel("РУЧНОЙ РЕДАКТОР БИЛДА")
        family = legacy.ensure_cormorant_loaded() or "Georgia"
        title.setFont(QFont(family, 17, QFont.DemiBold))
        title.setStyleSheet("color:#cfad65;")
        root.addWidget(title)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._passive_page(), "Пассивки")
        self.tabs.addTab(self._gem_page(), "Камни")
        root.addWidget(self.tabs, 1)

        bottom = QHBoxLayout()
        self.message = QLabel()
        self.message.setStyleSheet("color:#b8a982;")
        bottom.addWidget(self.message, 1)
        cancel = QPushButton("Отмена")
        save = QPushButton("Сохранить билд")
        cancel.setStyleSheet(_button())
        save.setStyleSheet(_button(True))
        cancel.clicked.connect(self.reject)
        save.clicked.connect(self._save)
        bottom.addWidget(cancel)
        bottom.addWidget(save)
        root.addLayout(bottom)

        self._loading = False
        self._load_state_to_controls()

    def _style(self):
        s = legacy.Style
        return f"""
            QDialog {{background:{s.BG}; color:{s.TEXT_PRIMARY};}}
            QWidget {{color:{s.TEXT_SECONDARY};}}
            QLabel {{background:transparent;}}
            QComboBox, QSpinBox, QListWidget {{background:{s.BG_SECONDARY}; color:{s.TEXT_PRIMARY};
                border:1px solid {s.BORDER}; border-radius:{s.RAD_S}px; padding:5px;}}
            QComboBox:focus, QSpinBox:focus, QListWidget:focus {{border-color:{s.ACCENT};}}
            QTabWidget::pane {{border:1px solid rgba(154,116,57,.35);}}
            QTabBar::tab {{background:{s.BG_SECONDARY}; padding:8px 18px; color:{s.TEXT_MUTED};}}
            QTabBar::tab:selected {{color:#e8dcc0; border-bottom:2px solid {s.ACCENT};}}
            QSplitter::handle {{background:rgba(154,116,57,.28);}}
        """

    def _passive_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(6, 6, 6, 6)
        controls = QHBoxLayout()
        controls.addWidget(QLabel("Класс"))
        self.class_combo = QComboBox()
        self.class_combo.addItems(CLASS_START_INDEX)
        controls.addWidget(self.class_combo)
        controls.addWidget(QLabel("Восхождение"))
        self.asc_combo = QComboBox()
        controls.addWidget(self.asc_combo)
        controls.addWidget(QLabel("Целевой уровень"))
        self.target_level = QSpinBox()
        self.target_level.setRange(1, 100)
        controls.addWidget(self.target_level)
        self.budget_label = QLabel()
        self.budget_label.setStyleSheet("color:#d5bb7b;")
        controls.addWidget(self.budget_label, 1)
        undo = QPushButton("Отменить ноду")
        fit = QPushButton("К выбранным")
        undo.setStyleSheet(_button())
        fit.setStyleSheet(_button())
        undo.clicked.connect(self._undo_node)
        fit.clicked.connect(self._fit_tree)
        controls.addWidget(undo)
        controls.addWidget(fit)
        layout.addLayout(controls)
        self.tree = ManualTreeCanvas()
        self.tree.node_clicked.connect(self._node_clicked)
        layout.addWidget(self.tree, 1)
        self.class_combo.currentTextChanged.connect(self._class_changed)
        self.asc_combo.currentTextChanged.connect(self._ascendancy_changed)
        self.target_level.valueChanged.connect(self._level_changed)
        return page

    def _gem_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(8, 8, 8, 8)
        top = QHBoxLayout()
        top.addWidget(QLabel("Этап"))
        self.stage_combo = QComboBox()
        self.stage_combo.currentIndexChanged.connect(self._stage_changed)
        top.addWidget(self.stage_combo, 1)
        top.addWidget(QLabel("с уровня"))
        self.stage_level = QSpinBox()
        self.stage_level.setRange(1, 100)
        self.stage_level.valueChanged.connect(self._stage_level_changed)
        top.addWidget(self.stage_level)
        for text, slot in (("Новый этап", self._new_stage), ("Удалить этап", self._delete_stage)):
            button = QPushButton(text)
            button.setStyleSheet(_button())
            button.clicked.connect(slot)
            top.addWidget(button)
        layout.addLayout(top)

        splitter = QSplitter(Qt.Horizontal)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("Связки"))
        self.link_list = QListWidget()
        self.link_list.currentRowChanged.connect(self._link_changed)
        left_layout.addWidget(self.link_list, 1)
        link_buttons = QHBoxLayout()
        for text, slot in (("+ Связка", self._new_link), ("− Связка", self._delete_link)):
            button = QPushButton(text)
            button.setStyleSheet(_button())
            button.clicked.connect(slot)
            link_buttons.addWidget(button)
        left_layout.addLayout(link_buttons)
        splitter.addWidget(left)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.addWidget(QLabel("Камни в выбранной связке"))
        self.gem_list = QListWidget()
        right_layout.addWidget(self.gem_list, 1)
        picker = QHBoxLayout()
        self.gem_combo = QComboBox()
        self.gem_combo.setEditable(True)
        catalog = json.loads((ROOT / "data" / "poe1" / "gem_catalog.json").read_text(encoding="utf-8"))
        self.gem_combo.addItems(sorted(item.get("name", key) for key, item in catalog.items()))
        self.support_check = QCheckBox("поддержка")
        add = QPushButton("Добавить")
        remove = QPushButton("Удалить камень")
        add.setStyleSheet(_button(True))
        remove.setStyleSheet(_button())
        add.clicked.connect(self._add_gem)
        remove.clicked.connect(self._remove_gem)
        picker.addWidget(self.gem_combo, 1)
        picker.addWidget(self.support_check)
        picker.addWidget(add)
        picker.addWidget(remove)
        right_layout.addLayout(picker)
        splitter.addWidget(right)
        splitter.setSizes([330, 650])
        layout.addWidget(splitter, 1)
        return page

    def _load_state_to_controls(self):
        self.class_combo.setCurrentText(self.state.get("class", "Witch"))
        self._fill_ascendancies(self.state.get("ascendancy"))
        self.target_level.setValue(int(self.state.get("level", self.profile.get("level", 1))))
        self._refresh_tree(first=True)
        self._refresh_stages()

    def _fill_ascendancies(self, selected=None):
        self.asc_combo.blockSignals(True)
        self.asc_combo.clear()
        self.asc_combo.addItems(ASCENDANCIES[self.class_combo.currentText()])
        if selected in ASCENDANCIES[self.class_combo.currentText()]:
            self.asc_combo.setCurrentText(selected)
        self.asc_combo.blockSignals(False)
        self.state["ascendancy"] = self.asc_combo.currentText()

    def _selected_regular(self):
        start = class_start_id(self.nodes, self.state["class"])
        return [start] + [str(node) for node in self.state["passives"]]

    def _selected_ascendancy(self):
        start = ascendancy_start_id(self.nodes, self.state["ascendancy"])
        return ([start] if start else []) + [str(node) for node in self.state["ascendancy_nodes"]]

    def _neighbors(self, node_id):
        node = self.nodes.get(str(node_id), {})
        return {str(value) for value in node.get("out", []) + node.get("in", [])}

    def _available(self):
        regular = set(self._selected_regular())
        asc = set(self._selected_ascendancy())
        result = set()
        if len(self.state["passives"]) + len(self.state["masteries"]) < passive_budget(self.target_level.value()):
            for node in regular:
                for other in self._neighbors(node):
                    data = self.nodes.get(other, {})
                    if not data.get("ascendancyName") and data.get("classStartIndex") is None and other not in regular:
                        result.add(other)
            for node_id, data in self.nodes.items():
                if data.get("isMastery") and node_id not in self.state["masteries"]:
                    if self._neighbors(node_id) & regular:
                        result.add(node_id)
        if len(self.state["ascendancy_nodes"]) < ascendancy_budget(self.target_level.value()):
            for node in asc:
                for other in self._neighbors(node):
                    data = self.nodes.get(other, {})
                    if data.get("ascendancyName") == self.state["ascendancy"] and other not in asc:
                        result.add(other)
        return result

    def _refresh_tree(self, first=False):
        regular = self._selected_regular()
        asc = self._selected_ascendancy()
        self.tree.set_editor_state(
            regular, self.state["masteries"], self.state["ascendancy"], asc,
        )
        self.tree.set_available(self._available())
        used = len(self.state["passives"]) + len(self.state["masteries"])
        budget = passive_budget(self.target_level.value())
        asc_used, asc_budget = len(self.state["ascendancy_nodes"]), ascendancy_budget(self.target_level.value())
        color = "#df6969" if used > budget or asc_used > asc_budget else "#d5bb7b"
        self.budget_label.setText(f"Пассивки {used}/{budget} · восхождение {asc_used}/{asc_budget}")
        self.budget_label.setStyleSheet(f"color:{color};")
        if first and regular[0] in self.tree.positions:
            self.tree.center = self.tree.positions[regular[0]]
            self.tree.scale = .18
            self.tree.update()

    def _fit_tree(self):
        selected = self._selected_regular() + self._selected_ascendancy()
        old = set(self.tree.selected)
        self.tree.selected = set(selected)
        self.tree.fit_selected()
        self.tree.selected = old
        self.tree.update()

    def _node_clicked(self, node_id):
        data = self.nodes.get(node_id, {})
        if data.get("classStartIndex") is not None:
            return self._flash("Старт класса выбирается списком сверху")
        if data.get("ascendancyName"):
            return self._toggle_ascendancy_node(node_id, data)
        if data.get("isMastery"):
            return self._toggle_mastery(node_id, data)
        return self._toggle_passive(node_id)

    def _toggle_passive(self, node_id):
        path = self.state["passives"]
        if node_id in path:
            if path and path[-1] == node_id:
                path.pop()
                self._refresh_tree()
            else:
                self._flash("Удалять можно только последнюю ноду маршрута")
            return
        if node_id not in self._available():
            return self._flash("Сначала выберите соседнюю ноду и проверьте запас очков")
        path.append(node_id)
        self._refresh_tree()

    def _toggle_mastery(self, node_id, node):
        if node_id in self.state["masteries"]:
            del self.state["masteries"][node_id]
            self._refresh_tree()
            return
        if node_id not in self._available():
            return self._flash("Сначала возьмите пассив в этом кластере")
        localized = localized_node(dict(node, _id=node_id))
        effects = localized.get("masteryEffects", [])
        labels = [" / ".join(effect.get("stats", [])) for effect in effects]
        choice, ok = QInputDialog.getItem(self, "Выберите эффект мастерства", node.get("name", "Mastery"), labels, 0, False)
        if not ok:
            return
        index = labels.index(choice)
        self.state["masteries"][node_id] = effects[index].get("effect")
        self._refresh_tree()

    def _toggle_ascendancy_node(self, node_id, node):
        if node.get("ascendancyName") != self.state["ascendancy"]:
            return self._flash("Эта нода относится к другому восхождению")
        start = ascendancy_start_id(self.nodes, self.state["ascendancy"])
        if node_id == start:
            return
        path = self.state["ascendancy_nodes"]
        if node_id in path:
            if path and path[-1] == node_id:
                path.pop()
                self._refresh_tree()
            else:
                self._flash("Удалять можно только последнюю ноду восхождения")
            return
        if node_id not in self._available():
            return self._flash("Нужна соседняя нода и свободное очко восхождения")
        path.append(node_id)
        self._refresh_tree()

    def _undo_node(self):
        if self.state["ascendancy_nodes"]:
            self.state["ascendancy_nodes"].pop()
        elif self.state["masteries"]:
            self.state["masteries"].popitem()
        elif self.state["passives"]:
            self.state["passives"].pop()
        self._refresh_tree()

    def _class_changed(self, class_name):
        if self._loading or not class_name:
            return
        if self.state.get("class") != class_name and (self.state["passives"] or self.state["masteries"]):
            answer = QMessageBox.question(self, "Сменить класс", "Маршрут пассивов будет очищен. Продолжить?")
            if answer != QMessageBox.Yes:
                self.class_combo.blockSignals(True)
                self.class_combo.setCurrentText(self.state["class"])
                self.class_combo.blockSignals(False)
                return
        self.state["class"] = class_name
        self.state["passives"] = []
        self.state["masteries"] = {}
        self.state["ascendancy_nodes"] = []
        self._fill_ascendancies()
        self._refresh_tree(first=True)

    def _ascendancy_changed(self, name):
        if self._loading or not name:
            return
        self.state["ascendancy"] = name
        self.state["ascendancy_nodes"] = []
        self._refresh_tree()

    def _level_changed(self, value):
        if self._loading:
            return
        self.state["level"] = value
        self._refresh_tree()

    def _current_stage(self):
        index = self.stage_combo.currentIndex()
        stages = self.state["gem_stages"]
        return stages[index] if 0 <= index < len(stages) else None

    def _current_link(self):
        stage = self._current_stage()
        row = self.link_list.currentRow()
        links = stage.get("links", []) if stage else []
        return links[row] if 0 <= row < len(links) else None

    def _refresh_stages(self, selected=0):
        stages = self.state["gem_stages"]
        self.stage_combo.blockSignals(True)
        self.stage_combo.clear()
        for stage in stages:
            self.stage_combo.addItem(f"Уровень {stage.get('level', 1)} · {stage.get('title', 'Камни')}")
        if stages:
            self.stage_combo.setCurrentIndex(max(0, min(selected, len(stages) - 1)))
        self.stage_combo.blockSignals(False)
        self._stage_changed(self.stage_combo.currentIndex())

    def _stage_changed(self, index):
        stage = self._current_stage()
        self.stage_level.blockSignals(True)
        self.stage_level.setValue(int(stage.get("level", 1)) if stage else 1)
        self.stage_level.blockSignals(False)
        self.link_list.clear()
        for number, link in enumerate(stage.get("links", []) if stage else [], 1):
            names = " — ".join(gem.get("name", "") for gem in link.get("gems", []))
            self.link_list.addItem(f"{number}. {names or 'Пустая связка'}")
        if self.link_list.count():
            self.link_list.setCurrentRow(0)
        else:
            self.gem_list.clear()

    def _stage_level_changed(self, value):
        stage = self._current_stage()
        if stage:
            stage["level"] = value
            stage["title"] = f"Manual gems from {value}"
            self._refresh_stages(self.stage_combo.currentIndex())

    def _new_stage(self):
        stages = self.state["gem_stages"]
        previous = self._current_stage()
        level = self.target_level.value()
        stages.append({
            "level": level,
            "title": f"Manual gems from {level}",
            "links": copy.deepcopy(previous.get("links", [])) if previous else [],
        })
        stages.sort(key=lambda item: int(item.get("level", 1)))
        self._refresh_stages(stages.index(next(item for item in stages if item["level"] == level)))

    def _delete_stage(self):
        index = self.stage_combo.currentIndex()
        if 0 <= index < len(self.state["gem_stages"]):
            self.state["gem_stages"].pop(index)
        self._refresh_stages(max(0, index - 1))

    def _new_link(self):
        stage = self._current_stage()
        if not stage:
            self._new_stage()
            stage = self._current_stage()
        stage.setdefault("links", []).append({"label": f"Связка {len(stage['links']) + 1}", "gems": []})
        self._stage_changed(self.stage_combo.currentIndex())
        self.link_list.setCurrentRow(self.link_list.count() - 1)

    def _delete_link(self):
        stage = self._current_stage()
        row = self.link_list.currentRow()
        if stage and 0 <= row < len(stage.get("links", [])):
            stage["links"].pop(row)
        self._stage_changed(self.stage_combo.currentIndex())

    def _link_changed(self, row):
        self.gem_list.clear()
        link = self._current_link()
        if not link:
            return
        for gem in link.get("gems", []):
            suffix = " [support]" if gem.get("support") else ""
            self.gem_list.addItem(gem.get("name", "") + suffix)

    def _add_gem(self):
        link = self._current_link()
        name = self.gem_combo.currentText().strip()
        if not link or not name:
            return self._flash("Сначала создайте и выберите связку")
        link.setdefault("gems", []).append({
            "name": name,
            "support": self.support_check.isChecked(),
            "level": "20",
            "quality": "0",
        })
        self._stage_changed(self.stage_combo.currentIndex())
        self.link_list.setCurrentRow(min(self.link_list.count() - 1, max(0, self.link_list.currentRow())))

    def _remove_gem(self):
        link = self._current_link()
        row = self.gem_list.currentRow()
        if link and 0 <= row < len(link.get("gems", [])):
            link["gems"].pop(row)
        self._link_changed(self.link_list.currentRow())
        self._stage_changed(self.stage_combo.currentIndex())

    def _flash(self, text):
        self.message.setText(text)
        QTimer.singleShot(2600, lambda: self.message.clear())

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
