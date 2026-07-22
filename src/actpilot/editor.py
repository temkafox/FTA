"""Живая линия ручного редактора билда: ManualBuildEditor v1..v10 и его канвасы/диалоги."""

from __future__ import annotations

import copy
import math

from PyQt5.QtCore import QEvent, QObject, QPoint, QPointF, Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QPainter, QPen
from PyQt5.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QHBoxLayout, QInputDialog,
    QLabel, QListWidget, QMessageBox, QPushButton, QSpinBox, QSplitter,
    QTabWidget, QVBoxLayout, QWidget,
)

import main as legacy
from actpilot.build_model import (
    ASCENDANCIES, CLASS_START_INDEX, SNAPSHOT_KEYS,
    ascendancy_budget, ascendancy_start_id, class_start_id, load_tree,
    normalize_passive_stages, passive_budget,
)
from actpilot.build_model import build_from_state_v4 as build_from_state
from actpilot.build_model import state_from_build_v4 as state_from_build
from actpilot.data_cache import game_data
from actpilot.paths import get_resource_dir
from poe1_ru_text import localized_node
from poe1_tree_renderer_v19 import ExplicitProgressionTreeCanvas
from poe1_tree_renderer_v20 import ZoomScaledNodeMixin


ROOT = get_resource_dir()


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
        catalog = game_data("gem_catalog.json")
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


ManualBuildEditorV1 = ManualBuildEditor


class ManualBuildEditor(ManualBuildEditorV1):
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
            poedb = game_data("poedb_gems_ru.json")
            source = (poedb.get(key) or {}).get("source", "")
            support = source.casefold().endswith("_support")
            if not source:
                icons = game_data("gem_icons.json")
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


ManualBuildEditorV2 = ManualBuildEditor


class ManualBuildEditor(ManualBuildEditorV2):
    def _load_state_to_controls(self):
        was_loading = self._loading
        self._loading = True
        self.class_combo.setCurrentText(self.state.get("class", "Witch"))
        self._fill_ascendancies(self.state.get("ascendancy"))
        self.target_level.setValue(int(self.state.get("level", self.profile.get("level", 1))))
        self._loading = was_loading
        self._refresh_tree(first=True)
        self._refresh_stages()


ManualBuildEditorV3 = ManualBuildEditor


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


class ManualBuildEditor(ManualBuildEditorV3):
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


ManualBuildEditorV4 = ManualBuildEditor


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


class ManualBuildEditor(ManualBuildEditorV4):
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
        catalog = game_data("gem_catalog.json")
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


ManualBuildEditorV5 = ManualBuildEditor


DEFAULT_PLAN_LEVEL = 100


class ManualBuildEditor(ManualBuildEditorV5):
    def __init__(self, overlay, parent=None):
        super().__init__(overlay, parent)
        self.setWindowOpacity(1.0)

        # A brand-new manual build used to inherit character level 1, giving a
        # 0/0 budget and making the tree appear broken. The editor describes
        # the finished route; the live profile level controls its playback.
        has_route = bool(
            self.state.get("passives")
            or self.state.get("masteries")
            or self.state.get("ascendancy_nodes")
        )
        if not has_route and int(self.state.get("level", 1)) <= 1:
            self.target_level.setValue(DEFAULT_PLAN_LEVEL)
            self.state["level"] = DEFAULT_PLAN_LEVEL
            self._refresh_tree(first=True)
            self.message.setText(
                "Выберите подсвеченную соседнюю ноду. Целевой уровень задаёт бюджет плана, "
                "а текущий уровень персонажа меняется отдельно."
            )

    def _save(self):
        used = len(self.state["passives"]) + len(self.state["masteries"])
        target = self.target_level.value()
        if used > passive_budget(target):
            return self._flash(
                "Выбрано больше пассивов, чем доступно на целевом уровне"
            )
        if len(self.state["ascendancy_nodes"]) > ascendancy_budget(target):
            return self._flash(
                "Выбрано больше очков восхождения, чем доступно на целевом уровне"
            )

        # Do not turn the live character into level 100 merely because the
        # user planned a level-100 tree.
        live_level = self.profile.get("level", 1)
        self.state["level"] = target
        self.profile["build"] = build_from_state(self.state)
        self.profile["level"] = live_level
        self.overlay.save_profiles()
        self.accept()


ManualBuildEditorV6 = ManualBuildEditor


class PopupRaiser(QObject):
    """Keep combo popups above the always-on-top editor on Windows."""

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Show:
            QTimer.singleShot(0, watched.raise_)
            QTimer.singleShot(0, watched.activateWindow)
        return False


class ManualBuildEditor(ManualBuildEditorV6):
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


ManualBuildEditorV7 = ManualBuildEditor


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


class ManualBuildEditor(ManualBuildEditorV7):
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


ManualBuildEditorV8 = ManualBuildEditor


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


# Ловушка: v5-класс резолвит ZoomSafeManualTreeCanvas как глобал в рантайме — имя обязано указывать на safe-канвас
ZoomSafeManualTreeCanvas = SafePanManualTreeCanvas


class ManualBuildEditor(ManualBuildEditorV8):
    def _focus_stage_start(self):
        regular = self._selected_regular()
        start = regular[0] if regular else None
        point = self.tree.positions.get(start) if start else None
        if point is None:
            return
        self.tree.center = QPointF(point.x(), point.y())
        self.tree.scale = .16
        self.tree.update()


ManualBuildEditorV9 = ManualBuildEditor


class ManualBuildEditor(ManualBuildEditorV9):
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


ManualBuildEditorV10 = ManualBuildEditor
