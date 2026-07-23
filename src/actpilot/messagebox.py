"""Единый тёмный стиль и хелпер для QMessageBox и диалоговых кнопок."""

from __future__ import annotations

from PyQt5 import sip
from PyQt5.QtWidgets import QMessageBox


BUTTON_QSS = """
QPushButton {
    min-width: 88px;
    min-height: 30px;
    padding: 3px 14px;
    color: #f2eee5;
    background-color: #292b32;
    border: 1px solid #555966;
    border-radius: 6px;
}
QPushButton:hover {
    background-color: #363943;
    border-color: #d0aa61;
}
QPushButton:default {
    color: #17181d;
    background-color: #d0aa61;
    border-color: #e3bf77;
    font-weight: 600;
}
"""

MESSAGE_STYLE = """
QMessageBox {
    background-color: #17181d;
}
QMessageBox QLabel {
    color: #f2eee5;
    background-color: transparent;
    font-size: 13px;
}
QMessageBox QLabel#qt_msgbox_label {
    min-width: 310px;
}
""" + BUTTON_QSS


_DEFAULT_LABELS = {
    QMessageBox.Ok: "ОК",
    QMessageBox.Yes: "Да",
    QMessageBox.No: "Нет",
}


def show_message(
    parent,
    icon: QMessageBox.Icon,
    title: str,
    text: str,
    buttons: QMessageBox.StandardButtons = QMessageBox.Ok,
    default_button: QMessageBox.StandardButton = QMessageBox.NoButton,
    labels: dict | None = None,
) -> int:
    """Показать сообщение, читаемое под тёмной темой приложения."""
    if parent is not None and sip.isdeleted(parent):
        parent = None
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setIcon(icon)
    box.setText(text)
    box.setStandardButtons(buttons)
    relabel = dict(_DEFAULT_LABELS)
    if labels:
        relabel.update(labels)
    for standard, label in relabel.items():
        button = box.button(standard)
        if button is not None:
            button.setText(label)
    if default_button != QMessageBox.NoButton:
        box.setDefaultButton(default_button)
    box.setStyleSheet(MESSAGE_STYLE)
    return box.exec_()
