"""Editable, copy-friendly Path of Exile regex library."""

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication, QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)


DEFAULT_REGEXES = [
    {"name": "3 Линк", "pattern": ".-.-."},
    {"name": "Три синих", "pattern": "b-b-b"},
]

class RegexDialog(QDialog):
    hidden = pyqtSignal()

    def __init__(self, entries, on_change, parent=None):
        super().__init__(parent)
        self.on_change = on_change
        self.rows = []
        self.setWindowTitle("Регэкспы")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_DeleteOnClose, False)
        self.setFixedSize(590, 680)
        self.setObjectName("regexDialog")
        self.setStyleSheet(STYLE)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(26, 18, 26, 18)
        outer.setSpacing(6)
        header = QHBoxLayout()
        title = QLabel("Регэкспы")
        title.setObjectName("title")
        header.addWidget(title)
        header.addStretch()
        close = QPushButton("✕")
        close.setObjectName("closeButton")
        close.setCursor(Qt.PointingHandCursor)
        close.setFixedSize(32, 32)
        close.setFont(QFont("Segoe UI Symbol", 13, QFont.Normal))
        close.clicked.connect(self.hide)
        header.addWidget(close)
        outer.addLayout(header)

        subtitle = QLabel(
            "Сохраняйте поисковые шаблоны и копируйте их одним нажатием."
        )
        subtitle.setObjectName("subtitle")
        subtitle.setWordWrap(True)
        outer.addWidget(subtitle)

        rule = QFrame()
        rule.setFrameShape(QFrame.HLine)
        rule.setObjectName("rule")
        outer.addWidget(rule)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.body = QWidget()
        self.rows_layout = QVBoxLayout(self.body)
        self.rows_layout.setContentsMargins(0, 0, 5, 0)
        self.rows_layout.setSpacing(16)
        self.rows_layout.setAlignment(Qt.AlignTop)
        scroll.setWidget(self.body)
        outer.addWidget(scroll, 1)

        for entry in entries or DEFAULT_REGEXES:
            self.add_row(entry.get("name", ""), entry.get("pattern", ""), notify=False)

        add = QPushButton("+  Добавить регэксп")
        add.setObjectName("addButton")
        add.setCursor(Qt.PointingHandCursor)
        add.setFixedHeight(38)
        add.clicked.connect(lambda: self.add_row("Новый регэксп", ""))
        outer.addWidget(add)
        note = QLabel("Все изменения сохраняются автоматически")
        note.setObjectName("note")
        outer.addWidget(note)

    def add_row(self, name, pattern, notify=True):
        holder = QWidget()
        holder.setObjectName("regexRow")
        holder.setFixedHeight(108)
        holder.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        column = QVBoxLayout(holder)
        column.setContentsMargins(2, 5, 2, 5)
        column.setSpacing(8)
        name_edit = QLineEdit(name)
        name_edit.setObjectName("nameInput")
        title_row = QHBoxLayout()
        title_row.addWidget(name_edit, 1)
        remove = QPushButton("Удалить")
        remove.setObjectName("removeButton")
        remove.setCursor(Qt.PointingHandCursor)
        remove.setFixedSize(72, 28)
        title_row.addWidget(remove)
        pattern_row = QHBoxLayout()
        pattern_edit = QLineEdit(pattern)
        pattern_edit.setPlaceholderText("Введите регулярное выражение")
        copy = QPushButton("Копировать")
        copy.setObjectName("copyButton")
        copy.setCursor(Qt.PointingHandCursor)
        copy.setFixedSize(108, 40)
        pattern_row.addWidget(pattern_edit, 1)
        pattern_row.addWidget(copy)
        column.addLayout(title_row)
        column.addLayout(pattern_row)
        divider = QFrame()
        divider.setObjectName("rowDivider")
        divider.setFrameShape(QFrame.HLine)
        column.addWidget(divider)
        row = {"holder": holder, "name": name_edit, "pattern": pattern_edit}
        self.rows.append(row)
        self.rows_layout.addWidget(holder)
        name_edit.editingFinished.connect(self._save)
        pattern_edit.editingFinished.connect(self._save)
        copy.clicked.connect(lambda _, field=pattern_edit, button=copy: self._copy(field.text(), button))
        remove.clicked.connect(lambda: self._remove(row))
        if notify:
            self._save()

    def _copy(self, pattern, button):
        if pattern.strip():
            QApplication.clipboard().setText(pattern.strip())
            button.setText("Скопировано")
            button.setProperty("copied", True)
            button.style().unpolish(button)
            button.style().polish(button)
            QTimer.singleShot(1400, lambda: self._reset_copy_button(button))

    @staticmethod
    def _reset_copy_button(button):
        if button is None:
            return
        button.setText("Копировать")
        button.setProperty("copied", False)
        button.style().unpolish(button)
        button.style().polish(button)

    def _remove(self, row):
        self.rows.remove(row)
        row["holder"].deleteLater()
        self._save()

    def _save(self):
        self.on_change([
            {"name": row["name"].text().strip(), "pattern": row["pattern"].text().strip()}
            for row in self.rows
        ])

    def hideEvent(self, event):
        self._save()
        super().hideEvent(event)
        self.hidden.emit()


STYLE = """
QDialog#regexDialog { background:#101416; border:1px solid #5c4a30; border-radius:14px; }
QWidget { color:#e8e2d8; background:transparent; font-family:'Segoe UI'; font-size:13px; }
QLabel#title { font-size:23px; color:#eee4d4; }
QLabel#subtitle { color:#96938c; font-size:12px; padding-bottom:3px; }
QFrame#rule { color:#292b2b; background:#292b2b; max-height:1px; border:0; }
QLabel#note { color:#85827b; font-size:11px; }
QWidget#regexRow { background:transparent; border:0; }
QFrame#rowDivider { background:#2b3031; color:#2b3031; border:0; max-height:1px; }
QLineEdit { background:#1a2023; color:#dad8d3; border:1px solid #343b3e; border-radius:7px; padding:0 12px; min-height:38px; }
QLineEdit:focus { border-color:#52685a; }
QLineEdit#nameInput { background:transparent; border:0; padding:0; min-height:26px; font-weight:600; color:#eee9df; }
QPushButton#closeButton { background:transparent; color:#b4976a; border:1px solid #493b28; border-radius:6px; font-size:18px; padding:0; }
QPushButton#copyButton { background:#17291c; color:#8de36d; border:1px solid #2d6638; border-radius:7px; font-size:12px; font-weight:600; }
QPushButton#copyButton:hover { background:#17261b; border-color:#4c9a55; }
QPushButton#copyButton[copied="true"] { background:#245c30; color:#e6ffe9; }
QPushButton#removeButton { background:transparent; color:#9b7770; border:0; font-size:11px; }
QPushButton#removeButton:hover { color:#f06f61; }
QPushButton#addButton { background:#151c1e; color:#9bd681; border:1px solid #31543a; border-radius:7px; }
QScrollArea { border:0; background:transparent; }
QScrollBar:vertical { width:8px; background:#111719; border-radius:4px; }
QScrollBar::handle:vertical { background:#66543a; border-radius:4px; min-height:35px; }
QScrollBar::handle:vertical:hover { background:#806b49; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background:transparent; }
"""
