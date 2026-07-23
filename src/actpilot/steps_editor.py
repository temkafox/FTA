"""Диалог ручного редактирования маршрута: акты и шаги гайда."""

from __future__ import annotations

import uuid

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView, QDialog, QFrame, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

from actpilot.base_widgets import WindowDragHeader
from actpilot.messagebox import MESSAGE_STYLE
from actpilot.persistence import load_json, save_json
from actpilot.steps import (
    DEFAULT_STEPS, DEFAULT_STEPS_POE2, GAME_POE2, get_steps_file,
    get_user_steps_file, normalize_steps,
)

_STEP_ID_ROLE = Qt.UserRole + 1


class StepsEditorDialog(QDialog):
    """Правит акты и шаги выбранной игры, пишет их в пользовательский JSON."""

    def __init__(self, game, parent=None):
        super().__init__(parent)
        self.game = game
        self.saved = False
        self._current_act_row = -1

        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.Dialog | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setWindowModality(Qt.ApplicationModal)
        self.setObjectName("stepsEditor")
        self.setStyleSheet(STYLE)
        self.setFixedSize(780, 620)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 14, 24, 18)
        outer.setSpacing(10)

        header = DragHeader(self)
        header.setFixedHeight(42)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(4, 0, 0, 0)
        title_text = "Редактор шагов — PoE 2" if game == GAME_POE2 else "Редактор шагов — PoE 1"
        title = QLabel(title_text)
        title.setAttribute(Qt.WA_TransparentForMouseEvents)
        title.setObjectName("dialogTitle")
        header_layout.addWidget(title)
        header_layout.addStretch()
        close = QPushButton("×")
        close.setObjectName("windowButton")
        close.setFixedSize(32, 32)
        close.setCursor(Qt.PointingHandCursor)
        close.clicked.connect(self.reject)
        header_layout.addWidget(close)
        outer.addWidget(header)

        panes = QHBoxLayout()
        panes.setSpacing(16)
        panes.addLayout(self._build_acts_pane(), 2)
        panes.addLayout(self._build_steps_pane(), 3)
        outer.addLayout(panes, 1)

        hint = QLabel(
            "Двойной клик — правка текста. Разметка цвета: {zone|Побережье}, "
            "{boss|Мервейл}, {quest|…}. Ключи: " + ", ".join(_MARKUP_KEYS) + "."
        )
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        outer.addWidget(hint)

        actions = QHBoxLayout()
        actions.setSpacing(12)
        reset = QPushButton("Сбросить к стандартным")
        reset.setObjectName("secondaryButton")
        reset.setFixedHeight(40)
        reset.clicked.connect(self._reset_to_defaults)
        actions.addWidget(reset)
        actions.addStretch()
        cancel = QPushButton("Отмена")
        cancel.setObjectName("cancelButton")
        cancel.setFixedHeight(44)
        cancel.clicked.connect(self.reject)
        actions.addWidget(cancel)
        save = QPushButton("Сохранить")
        save.setObjectName("saveButton")
        save.setFixedHeight(44)
        save.clicked.connect(self._on_save)
        actions.addWidget(save)
        outer.addLayout(actions)

        self._load_into_widgets(self._read_current_steps())

    def _build_acts_pane(self):
        column = QVBoxLayout()
        column.setSpacing(6)
        label = QLabel("Акты")
        label.setObjectName("paneTitle")
        column.addWidget(label)
        self.acts_list = QListWidget()
        self.acts_list.setObjectName("actsList")
        self.acts_list.setEditTriggers(
            QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed
        )
        self.acts_list.currentRowChanged.connect(self._on_act_changed)
        column.addWidget(self.acts_list, 1)
        column.addLayout(self._list_buttons(
            self._add_act, self._remove_act,
            lambda: self._move_item(self.acts_list, -1),
            lambda: self._move_item(self.acts_list, 1),
            add_label="+ Акт",
        ))
        return column

    def _build_steps_pane(self):
        column = QVBoxLayout()
        column.setSpacing(6)
        label = QLabel("Шаги акта")
        label.setObjectName("paneTitle")
        column.addWidget(label)
        self.steps_list = QListWidget()
        self.steps_list.setObjectName("stepsList")
        self.steps_list.setWordWrap(True)
        self.steps_list.setEditTriggers(
            QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed
        )
        column.addWidget(self.steps_list, 1)
        column.addLayout(self._list_buttons(
            self._add_step, self._remove_step,
            lambda: self._move_item(self.steps_list, -1),
            lambda: self._move_item(self.steps_list, 1),
            add_label="+ Шаг",
        ))
        return column

    def _list_buttons(self, on_add, on_remove, on_up, on_down, add_label):
        row = QHBoxLayout()
        row.setSpacing(6)
        add = QPushButton(add_label)
        add.setObjectName("secondaryButton")
        add.clicked.connect(on_add)
        remove = QPushButton("Удалить")
        remove.setObjectName("secondaryButton")
        remove.clicked.connect(on_remove)
        up = QPushButton("↑")
        up.setObjectName("secondaryButton")
        up.setFixedWidth(40)
        up.clicked.connect(on_up)
        down = QPushButton("↓")
        down.setObjectName("secondaryButton")
        down.setFixedWidth(40)
        down.clicked.connect(on_down)
        for button in (add, remove, up, down):
            button.setFixedHeight(34)
            row.addWidget(button)
        return row

    def _read_current_steps(self):
        default = DEFAULT_STEPS_POE2 if self.game == GAME_POE2 else DEFAULT_STEPS
        return normalize_steps(load_json(get_steps_file(self.game), default))[0]

    def _load_into_widgets(self, data):
        self._current_act_row = -1
        self.acts_list.blockSignals(True)
        self.acts_list.clear()
        self.steps_list.clear()
        for name, steps in data.items():
            item = QListWidgetItem(name)
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            item.setData(Qt.UserRole, list(steps))
            self.acts_list.addItem(item)
        self.acts_list.blockSignals(False)
        if self.acts_list.count():
            self.acts_list.setCurrentRow(0)

    def _flush_steps_to_act(self):
        if 0 <= self._current_act_row < self.acts_list.count():
            steps = [
                {
                    "id": self.steps_list.item(i).data(_STEP_ID_ROLE),
                    "text": self.steps_list.item(i).text(),
                }
                for i in range(self.steps_list.count())
            ]
            self.acts_list.item(self._current_act_row).setData(Qt.UserRole, steps)

    def _on_act_changed(self, row):
        self._flush_steps_to_act()
        self.steps_list.clear()
        self._current_act_row = row
        if row < 0:
            return
        for step in self.acts_list.item(row).data(Qt.UserRole) or []:
            item = QListWidgetItem(step.get("text", ""))
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            item.setData(_STEP_ID_ROLE, step.get("id") or uuid.uuid4().hex)
            self.steps_list.addItem(item)

    def _add_act(self):
        item = QListWidgetItem(f"Act {self.acts_list.count() + 1}")
        item.setFlags(item.flags() | Qt.ItemIsEditable)
        item.setData(Qt.UserRole, [])
        self.acts_list.addItem(item)
        self.acts_list.setCurrentItem(item)
        self.acts_list.editItem(item)

    def _remove_act(self):
        row = self.acts_list.currentRow()
        if row < 0:
            return
        self._current_act_row = -1  # снимаем привязку, чтобы не вернуть шаги в удалённый акт
        self.acts_list.takeItem(row)

    def _add_step(self):
        if self.acts_list.currentRow() < 0:
            return
        item = QListWidgetItem("Новый шаг")
        item.setFlags(item.flags() | Qt.ItemIsEditable)
        item.setData(_STEP_ID_ROLE, uuid.uuid4().hex)
        self.steps_list.addItem(item)
        self.steps_list.setCurrentItem(item)
        self.steps_list.editItem(item)

    def _remove_step(self):
        row = self.steps_list.currentRow()
        if row >= 0:
            self.steps_list.takeItem(row)

    @staticmethod
    def _move_item(widget, delta):
        row = widget.currentRow()
        target = row + delta
        if row < 0 or not (0 <= target < widget.count()):
            return
        item = widget.takeItem(row)
        widget.insertItem(target, item)
        widget.setCurrentRow(target)

    def _reset_to_defaults(self):
        box = QMessageBox(self)
        box.setWindowTitle("Сброс шагов")
        box.setIcon(QMessageBox.Warning)
        box.setText(
            "Заменить текущие шаги стандартным маршрутом?\n"
            "Изменения в редакторе будут потеряны."
        )
        reset_button = box.addButton("Сбросить", QMessageBox.AcceptRole)
        box.addButton("Отмена", QMessageBox.RejectRole)
        box.setStyleSheet(MESSAGE_STYLE)
        box.exec_()
        if box.clickedButton() is reset_button:
            default = DEFAULT_STEPS_POE2 if self.game == GAME_POE2 else DEFAULT_STEPS
            self._load_into_widgets(normalize_steps(default)[0])

    def _collect(self):
        self._flush_steps_to_act()
        data = {}
        for i in range(self.acts_list.count()):
            item = self.acts_list.item(i)
            name = item.text().strip()
            if not name:
                return None, "Название акта не может быть пустым."
            if name in data:
                return None, f"Акт «{name}» указан дважды. Названия должны быть разными."
            steps = []
            for step in item.data(Qt.UserRole) or []:
                text = (step.get("text") or "").strip()
                if text:
                    steps.append({"id": step.get("id") or uuid.uuid4().hex, "text": text})
            data[name] = steps
        if not data:
            return None, "Нужен хотя бы один акт."
        return data, None

    def _warn(self, text):
        box = QMessageBox(self)
        box.setWindowTitle("Редактор шагов")
        box.setIcon(QMessageBox.Warning)
        box.setText(text)
        box.setStyleSheet(MESSAGE_STYLE)
        box.exec_()

    def _on_save(self):
        data, error = self._collect()
        if error:
            self._warn(error)
            return
        try:
            save_json(get_user_steps_file(self.game), data)
        except OSError as exc:
            self._warn(f"Не удалось сохранить шаги: {exc}")
            return
        self.saved = True
        self.accept()


class DragHeader(WindowDragHeader):
    def __init__(self, dialog):
        super().__init__(dialog)
        self.setObjectName("dragHeader")


_MARKUP_KEYS = ("boss", "zone", "npc", "quest", "unique", "item", "magic")


STYLE = """
QDialog#stepsEditor { background:#101517; border:1px solid #6e522c; border-radius:12px; }
QWidget { color:#ded8cc; font-family:'Segoe UI'; font-size:13px; }
QFrame#dragHeader { background:transparent; border-bottom:1px solid #403522; }
QLabel#dialogTitle { color:#ece3d3; font-size:21px; font-weight:600; }
QLabel#paneTitle { color:#79ce55; font-size:14px; font-weight:600; }
QLabel#hint { color:#9e978c; font-size:11px; }
QListWidget { background:#171d1f; color:#e8ddc8; border:1px solid #484136; border-radius:7px; padding:4px; outline:0; }
QListWidget::item { padding:6px 8px; border-radius:5px; }
QListWidget::item:selected { background:#22402a; color:#f0eadf; }
QListWidget::item:hover { background:#1c2426; }
QLineEdit { background:#0e1315; color:#f0e7d3; border:1px solid #8d7042; border-radius:4px; }
QPushButton#secondaryButton, QPushButton#cancelButton { background:#171d1f; color:#d3c8b5; border:1px solid #484136; border-radius:6px; padding:0 12px; }
QPushButton#secondaryButton:hover, QPushButton#cancelButton:hover { background:#20282a; border-color:#77684f; }
QPushButton#cancelButton { font-size:15px; min-width:96px; }
QPushButton#saveButton { color:#f0eadf; background:#236336; border:1px solid #4b8d59; border-radius:7px; font-size:15px; font-weight:600; min-width:120px; }
QPushButton#saveButton:hover { background:#1d713a; }
QPushButton#windowButton { background:transparent; color:#b9aa90; border:0; border-radius:6px; font-size:16px; }
QPushButton#windowButton:hover { background:#202729; color:#f0d69b; }
QScrollBar:vertical { background:#111719; width:8px; border-radius:4px; }
QScrollBar::handle:vertical { background:#66543a; border-radius:4px; min-height:35px; }
QScrollBar::handle:vertical:hover { background:#806b49; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background:transparent; }
"""
