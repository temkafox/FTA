"""Dark fantasy settings dialog used by the packaged ActPilot application."""

from pathlib import Path

from PyQt5 import sip
from PyQt5.QtCore import QSize, Qt, QTimer
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtWidgets import (
    QApplication, QButtonGroup, QDialog, QFileDialog, QFrame, QHBoxLayout,
    QLabel, QLineEdit, QMessageBox, QPushButton, QRadioButton, QScrollArea,
    QSlider, QVBoxLayout, QWidget,
)

from auto_update import UPDATE_DIALOG_STYLE as MESSAGE_STYLE, add_update_controls

import actpilot.shared as legacy


def capture_hotkey(key, modifiers):
    """None — клавишу нельзя отдать глобальному хоткею: Win не знает pynput, буква без Ctrl/Alt перестанет доходить до игры."""
    if modifiers & Qt.MetaModifier:
        return None
    parts = []
    if modifiers & Qt.ControlModifier:
        parts.append("Ctrl")
    if modifiers & Qt.AltModifier:
        parts.append("Alt")
    if modifiers & Qt.ShiftModifier:
        parts.append("Shift")
    if Qt.Key_F1 <= key <= Qt.Key_F24:
        parts.append(f"F{key - Qt.Key_F1 + 1}")
        return "+".join(parts)
    is_alnum = Qt.Key_A <= key <= Qt.Key_Z or Qt.Key_0 <= key <= Qt.Key_9
    if is_alnum and modifiers & (Qt.ControlModifier | Qt.AltModifier):
        parts.append(chr(key))
        return "+".join(parts)
    return None


class WheelSafeSlider(QSlider):
    """Let the settings page scroll without accidentally changing a value."""

    def wheelEvent(self, event):
        event.ignore()


class HotkeyButton(QPushButton):
    def __init__(self, value, parent=None):
        super().__init__(value, parent)
        self.value = value
        self.setObjectName("hotkeyButton")
        self.setFixedSize(124, 38)
        self.clicked.connect(self._capture)

    def _capture(self):
        self.setText("Нажмите клавишу…")
        self.setProperty("capturing", True)
        self.style().unpolish(self)
        self.style().polish(self)
        self.setFocus(Qt.MouseFocusReason)
        self.grabKeyboard()

    def keyPressEvent(self, event):
        if not self.property("capturing"):
            return super().keyPressEvent(event)
        if event.key() == Qt.Key_Escape:
            self._finish(self.value)
            return
        if event.key() in (Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta):
            return
        combo = capture_hotkey(event.key(), event.modifiers())
        if combo is None:
            self._flash_unsupported()
            return
        self._finish(combo)

    def _flash_unsupported(self):
        self.setText("Недоступная клавиша")

        def restore():
            if sip.isdeleted(self) or not self.property("capturing"):
                return
            self.setText("Нажмите клавишу…")

        QTimer.singleShot(900, restore)

    def focusOutEvent(self, event):
        if self.property("capturing"):
            self._finish(self.value)
        super().focusOutEvent(event)

    def _finish(self, value):
        self.releaseKeyboard()
        self.value = value
        self.setText(value)
        self.setProperty("capturing", False)
        self.style().unpolish(self)
        self.style().polish(self)


class DragHeader(QFrame):
    def __init__(self, dialog):
        super().__init__(dialog)
        self.dialog = dialog
        self.offset = None
        self.setObjectName("dragHeader")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.offset = event.globalPos() - self.dialog.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self.offset is not None and event.buttons() & Qt.LeftButton:
            self.dialog.move(event.globalPos() - self.offset)

    def mouseReleaseEvent(self, event):
        self.offset = None


class ActPilotSettingsDialog(QDialog):
    def __init__(self, settings, legacy, parent=None):
        super().__init__(parent)
        self.legacy = legacy
        self.settings = settings.copy()
        self._should_reset = False
        screen = QApplication.primaryScreen()
        area = screen.availableGeometry() if screen else None
        width = min(680, int(area.width() * .88)) if area else 680
        height = min(720, int(area.height() * .88)) if area else 720
        self.setFixedSize(width, height)
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.Dialog | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setWindowModality(Qt.ApplicationModal)
        self.setObjectName("settingsDialog")
        self.setStyleSheet(STYLE)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(26, 16, 26, 18)
        outer.setSpacing(9)
        header = DragHeader(self)
        header.setFixedHeight(46)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(4, 0, 0, 0)
        title = QLabel("Настройки")
        title.setAttribute(Qt.WA_TransparentForMouseEvents)
        title.setObjectName("dialogTitle")
        header_layout.addWidget(title)
        header_layout.addStretch()
        close = QPushButton("")
        close.setObjectName("windowButton")
        close.setFixedSize(32, 32)
        close_icon = legacy.scaled_ui_pixmap("close", 28, 28)
        if not close_icon.isNull():
            close.setIcon(QIcon(close_icon))
            close.setIconSize(QSize(28, 28))
        else:
            close.setText("×")
            close.setFont(QFont("Segoe UI Symbol", 16, QFont.Normal))
        close.setCursor(Qt.PointingHandCursor)
        close.clicked.connect(self.reject)
        header_layout.addWidget(close)
        outer.addWidget(header)

        scroll = QScrollArea()
        scroll.setObjectName("settingsScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)
        body = QWidget()
        body.setObjectName("scrollBody")
        self.content = QVBoxLayout(body)
        self.content.setContentsMargins(2, 1, 8, 1)
        self.content.setSpacing(10)

        box, section = self._section("1", "Игра")
        games = QHBoxLayout()
        self.poe1_radio = QRadioButton("Path of Exile 1")
        self.poe2_radio = QRadioButton("Path of Exile 2")
        self.game_group = QButtonGroup(self)
        self.game_group.addButton(self.poe1_radio)
        self.game_group.addButton(self.poe2_radio)
        current_game = settings.get("game", legacy.GAME_POE1)
        self.poe1_radio.setChecked(current_game == legacy.GAME_POE1)
        self.poe2_radio.setChecked(current_game == legacy.GAME_POE2)
        self.poe1_radio.setMinimumWidth(145)
        self.poe2_radio.setMinimumWidth(145)
        games.addWidget(self.poe1_radio)
        games.addWidget(self.poe2_radio)
        games.addStretch()
        section.addLayout(games)
        section.addWidget(self._label("Путь к Client.txt", "fieldLabel"))
        path_row = QHBoxLayout()
        self.client_path_input = QLineEdit(settings.get("poe1_client_path", ""))
        self.client_path_input.setPlaceholderText("Автопоиск или путь к Client.txt")
        self.client_path_input.setFixedHeight(38)
        browse = QPushButton("Обзор")
        browse.setObjectName("secondaryButton")
        browse.setFixedSize(88, 38)
        browse.clicked.connect(self._browse_client_log)
        path_row.addWidget(self.client_path_input, 1)
        path_row.addWidget(browse)
        section.addLayout(path_row)
        client_warning = self._label(
            "Укажите Client.txt. Обычно: steamapps/common/Path of Exile/logs/Client.txt",
            "warning",
        )
        client_warning.setWordWrap(True)
        section.addWidget(client_warning)
        self.content.addWidget(box)

        box, section = self._section("2", "Поведение оверлея")
        from PyQt5.QtWidgets import QCheckBox
        self.click_through_checkbox = QCheckBox("Клики сквозь оверлей")
        self.click_through_checkbox.setChecked(settings.get("click_through", False))
        section.addWidget(self.click_through_checkbox)
        self.show_splits_checkbox = QCheckBox("Показывать отсечки времени по шагам")
        self.show_splits_checkbox.setChecked(settings.get("show_step_splits", True))
        section.addWidget(self.show_splits_checkbox)
        self.opacity_slider = self._slider(section, "Прозрачность оверлея", 50, 100,
                                           int(settings.get("opacity", .95) * 100))
        self.scale_slider = self._slider(section, "Масштаб интерфейса",
            int(legacy.Style.UI_SCALE_MIN * 100), int(legacy.Style.UI_SCALE_MAX * 100),
            int(settings.get("ui_scale", 1.0) * 100))
        self.content.addWidget(box)

        box, section = self._section("3", "Горячие клавиши")
        self.previous_hotkey_input = self._hotkey(section, "Предыдущий шаг", legacy.display_hotkey(
            settings.get("previous_hotkey", legacy.DEFAULT_SETTINGS["previous_hotkey"])))
        self.hotkey_input = self._hotkey(section, "Следующий шаг", legacy.display_hotkey(
            settings.get("hotkey", legacy.DEFAULT_SETTINGS["hotkey"])))
        self.layout_hotkey_input = self._hotkey(section, "Мини-панель (камни и дерево)", legacy.display_hotkey(
            settings.get("layout_hotkey", legacy.DEFAULT_SETTINGS["layout_hotkey"])))
        self.regex_hotkey_input = self._hotkey(section, "Открыть регэкспы", legacy.display_hotkey(
            settings.get("regex_hotkey", legacy.DEFAULT_SETTINGS["regex_hotkey"])))
        from PyQt5.QtWidgets import QCheckBox
        self.hide_hotkey_hints_checkbox = QCheckBox("Скрыть хоткей-подсказки")
        self.hide_hotkey_hints_checkbox.setChecked(not settings.get("show_hotkey_hints", True))
        section.addWidget(self.hide_hotkey_hints_checkbox)
        self.content.addWidget(box)
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

        reset = QPushButton("Сбросить прогресс")
        reset.setObjectName("dangerButton")
        reset.setFixedHeight(40)
        reset.clicked.connect(self._reset)
        outer.addWidget(reset)
        actions = QHBoxLayout()
        actions.setSpacing(14)
        cancel = QPushButton("Отмена")
        cancel.setObjectName("cancelButton")
        cancel.clicked.connect(self.reject)
        save = QPushButton("Сохранить")
        save.setObjectName("saveButton")
        save.clicked.connect(self._on_save)
        for button in (cancel, save):
            button.setFixedHeight(46)
            actions.addWidget(button)
        outer.addLayout(actions)

    def showEvent(self, event):
        super().showEvent(event)
        self.raise_()
        self.activateWindow()

    @staticmethod
    def _label(text, name):
        label = QLabel(text)
        label.setObjectName(name)
        return label

    def _section(self, number, title):
        box = QFrame()
        box.setObjectName("section")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(4, 8, 4, 12)
        layout.setSpacing(8)
        heading = QHBoxLayout()
        heading.addWidget(self._label(title, "sectionTitle"))
        heading.addStretch()
        layout.addLayout(heading)
        return box, layout

    def _slider(self, layout, text, minimum, maximum, value):
        row = QHBoxLayout()
        slider = WheelSafeSlider(Qt.Horizontal)
        slider.setFocusPolicy(Qt.ClickFocus)
        slider.setRange(minimum, maximum)
        slider.setValue(value)
        value_label = self._label(f"{value}%", "valueLabel")
        value_label.setFixedWidth(45)
        value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        slider.valueChanged.connect(lambda value, label=value_label: label.setText(f"{value}%"))
        row.addWidget(QLabel(text))
        row.addWidget(slider, 1)
        row.addWidget(value_label)
        layout.addLayout(row)
        return slider

    @staticmethod
    def _hotkey(layout, text, value):
        row = QHBoxLayout()
        button = HotkeyButton(value)
        row.addWidget(QLabel(text))
        row.addStretch()
        row.addWidget(button)
        layout.addLayout(row)
        return button

    def _browse_client_log(self):
        current = self.client_path_input.text().strip()
        start = str(Path(current).parent) if current else ""
        path, _ = QFileDialog.getOpenFileName(
            self, "Выберите Client.txt", start, "Client log (Client.txt);;Text files (*.txt)")
        if path:
            self.client_path_input.setText(path)

    def _on_save(self):
        assignments = (
            ("Предыдущий шаг", self.previous_hotkey_input),
            ("Следующий шаг", self.hotkey_input),
            ("Мини-панель (камни и дерево)", self.layout_hotkey_input),
            ("Открыть регэкспы", self.regex_hotkey_input),
        )
        seen = {}
        for label, button in assignments:
            normalized = self.legacy.normalize_hotkey(button.value)
            if normalized in seen:
                self._should_reset = False
                box = QMessageBox(self)
                box.setWindowTitle("Настройки")
                box.setIcon(QMessageBox.Warning)
                box.setText(
                    f"Клавиша «{self.legacy.display_hotkey(button.value)}» назначена сразу "
                    f"на «{seen[normalized]}» и «{label}».\nНазначьте разные клавиши."
                )
                box.setStyleSheet(MESSAGE_STYLE)
                box.exec_()
                return
            seen[normalized] = label
        self.accept()

    def _reset(self):
        box = QMessageBox(self)
        box.setWindowTitle("Сброс прогресса")
        box.setIcon(QMessageBox.Warning)
        box.setText("Сбросить прогресс прохождения?\nОтметки шагов и таймер будут очищены.")
        reset_button = box.addButton("Сбросить", QMessageBox.AcceptRole)
        box.addButton("Отмена", QMessageBox.RejectRole)
        box.setStyleSheet(MESSAGE_STYLE)
        box.exec_()
        if box.clickedButton() is not reset_button:
            return
        self._should_reset = True
        self._on_save()

    def get_settings(self):
        legacy = self.legacy
        self.settings.update({
            "previous_hotkey": legacy.normalize_hotkey(self.previous_hotkey_input.value),
            "hotkey": legacy.normalize_hotkey(self.hotkey_input.value),
            "layout_hotkey": legacy.normalize_hotkey(self.layout_hotkey_input.value),
            "regex_hotkey": legacy.normalize_hotkey(self.regex_hotkey_input.value),
            "opacity": self.opacity_slider.value() / 100,
            "layout_opacity": self.settings.get(
                "layout_opacity", legacy.DEFAULT_SETTINGS["layout_opacity"]),
            "game": legacy.GAME_POE2 if self.poe2_radio.isChecked() else legacy.GAME_POE1,
            "click_through": self.click_through_checkbox.isChecked(),
            "show_step_splits": self.show_splits_checkbox.isChecked(),
            "show_hotkey_hints": not self.hide_hotkey_hints_checkbox.isChecked(),
            "ui_scale": self.scale_slider.value() / 100.0,
            "poe1_client_path": self.client_path_input.text().strip(),
        })
        return self.settings

    @property
    def should_reset(self):
        return self._should_reset


STYLE = """
QDialog#settingsDialog { background:#101517; border:1px solid #6e522c; border-radius:12px; }
QWidget { color:#ded8cc; font-family:'Segoe UI'; font-size:13px; }
QFrame#dragHeader { background:transparent; border-bottom:1px solid #403522; }
QLabel#dialogTitle { color:#ece3d3; font-size:23px; font-weight:600; }
QScrollArea#settingsScroll, QWidget#scrollBody { background:transparent; border:0; }
QFrame#section { background:transparent; border:0; border-bottom:1px solid #332d23; border-radius:0; }
QLabel#sectionTitle { color:#79ce55; font-size:16px; font-weight:600; }
QLabel#hint { color:#9e978c; font-size:11px; }
QLabel#warning { color:#ef6b5c; font-size:11px; }
QLabel#valueLabel { color:#83dd56; font-size:15px; }
QLineEdit { background:#171d1f; color:#e8ddc8; border:1px solid #484136; border-radius:6px; padding:0 11px; }
QLineEdit:focus { border-color:#8d7042; }
QRadioButton, QCheckBox { spacing:9px; font-size:14px; }
QRadioButton::indicator, QCheckBox::indicator { width:19px; height:19px; border:1px solid #62543d; border-radius:4px; background:#171d1f; }
QRadioButton::indicator { border-radius:11px; }
QRadioButton::indicator:checked, QCheckBox::indicator:checked { background:#54b94e; border:4px solid #17331b; }
QSlider::groove:horizontal { background:#2b2c2b; height:6px; border-radius:3px; }
QSlider::sub-page:horizontal { background:#5dcc5b; border-radius:3px; }
QSlider::handle:horizontal { background:#70d15d; border:2px solid #806335; width:14px; margin:-6px 0; border-radius:9px; }
QPushButton#windowButton { background:transparent; color:#b9aa90; border:0; border-radius:6px; padding:0; margin:0; }
QPushButton#windowButton:hover { background:#202729; color:#f0d69b; }
QPushButton#hotkeyButton { background:#171d1f; color:#eadfc9; border:1px solid #484136; border-radius:6px; font-size:14px; }
QPushButton#hotkeyButton:hover { border-color:#8d7042; background:#1c2426; }
QPushButton#hotkeyButton[capturing="true"] { color:#78d958; border-color:#78d958; font-size:11px; }
QPushButton#secondaryButton, QPushButton#cancelButton { background:#171d1f; color:#d3c8b5; border:1px solid #484136; border-radius:6px; }
QPushButton#secondaryButton:hover, QPushButton#cancelButton:hover { background:#20282a; border-color:#77684f; }
QPushButton#dangerButton { background:transparent; color:#ef6b5c; border:1px solid #8e382f; border-radius:8px; font-size:14px; }
QPushButton#saveButton { color:#f0eadf; background:#236336; border:1px solid #4b8d59; border-radius:7px; font-size:15px; font-weight:600; }
QPushButton#saveButton:hover { background:#1d713a; }
QPushButton#cancelButton { font-size:16px; }
QScrollBar:vertical { background:#111719; width:8px; border-radius:4px; }
QScrollBar::handle:vertical { background:#66543a; border-radius:4px; min-height:35px; }
QScrollBar::handle:vertical:hover { background:#806b49; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background:transparent; }
"""


class UpdateSettingsDialog(ActPilotSettingsDialog):
    def __init__(self, settings, parent=None):
        super().__init__(settings, legacy, parent)
        add_update_controls(self)
