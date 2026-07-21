"""ActPilot PoE 1 launcher with character profiles and PoB leveling view."""

from __future__ import annotations

import html
import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication, QComboBox, QDialog, QFrame, QHBoxLayout, QInputDialog,
    QLabel, QMessageBox, QPushButton, QScrollArea, QTabWidget, QTextEdit,
    QVBoxLayout, QWidget,
)

import main as legacy
from poe1_builds import (
    LEVEL_MAX, LEVEL_MIN, PobImportError, Poe1ProfileStore, clamp_level,
    new_profile, parse_pob, stage_for_level,
)


PROFILE_FILE = legacy.DATA_DIR / "poe1_characters.json"


def button_style(accent=False):
    background = legacy.Style.ACCENT if accent else legacy.Style.BG_SECONDARY
    color = legacy.Style.BG if accent else legacy.Style.TEXT_SECONDARY
    return f"""
        QPushButton {{
            background: {background}; border: 1px solid {legacy.Style.BORDER};
            border-radius: 7px; color: {color}; padding: 7px 12px;
        }}
        QPushButton:hover {{ border-color: {legacy.Style.ACCENT}; color: white; }}
    """


class PobImportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Импорт Path of Building — PoE 1")
        self.resize(620, 430)
        self.setStyleSheet(
            f"QDialog {{ background:{legacy.Style.BG}; color:{legacy.Style.TEXT_PRIMARY}; }}"
        )
        layout = QVBoxLayout(self)
        title = QLabel("Вставьте полный код Export Build из Path of Building")
        title.setFont(QFont("Segoe UI", 13, QFont.DemiBold))
        layout.addWidget(title)
        hint = QLabel(
            "Лучше использовать leveling PoB с деревьями и Skill Sets, "
            "названными Level 12, Level 24 и т. п. Ссылки pobb.in пока не загружаются."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color:{legacy.Style.TEXT_MUTED};")
        layout.addWidget(hint)
        self.editor = QTextEdit()
        self.editor.setPlaceholderText("PoB code или <PathOfBuilding>...</PathOfBuilding>")
        self.editor.setStyleSheet(
            f"background:{legacy.Style.BG_SECONDARY}; color:{legacy.Style.TEXT_PRIMARY}; "
            f"border:1px solid {legacy.Style.BORDER}; padding:8px;"
        )
        layout.addWidget(self.editor, 1)
        row = QHBoxLayout()
        cancel = QPushButton("Отмена")
        cancel.setStyleSheet(button_style())
        cancel.clicked.connect(self.reject)
        accept = QPushButton("Импортировать")
        accept.setStyleSheet(button_style(True))
        accept.clicked.connect(self.accept)
        row.addStretch()
        row.addWidget(cancel)
        row.addWidget(accept)
        layout.addLayout(row)

    def source(self):
        return self.editor.toPlainText().strip()


class BuildProgressDialog(QDialog):
    def __init__(self, overlay):
        super().__init__(overlay)
        self.overlay = overlay
        self.setWindowTitle("Персонаж и прокачка — PoE 1")
        self.setWindowFlags(Qt.Dialog | Qt.WindowStaysOnTopHint)
        self.resize(760, 670)
        self.setMinimumSize(620, 500)
        self.setStyleSheet(f"""
            QDialog {{ background:{legacy.Style.BG}; color:{legacy.Style.TEXT_PRIMARY}; }}
            QLabel {{ color:{legacy.Style.TEXT_SECONDARY}; }}
            QComboBox {{ background:{legacy.Style.BG_SECONDARY}; color:white;
                border:1px solid {legacy.Style.BORDER}; padding:7px; min-height:24px; }}
            QTabWidget::pane {{ border:1px solid {legacy.Style.BORDER}; }}
            QTabBar::tab {{ background:{legacy.Style.BG_SECONDARY}; color:{legacy.Style.TEXT_MUTED};
                padding:9px 18px; }}
            QTabBar::tab:selected {{ color:white; border-bottom:2px solid {legacy.Style.ACCENT}; }}
        """)
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        profile_row = QHBoxLayout()
        profile_row.addWidget(QLabel("Персонаж:"))
        self.profile_combo = QComboBox()
        self.profile_combo.currentIndexChanged.connect(self._profile_changed)
        profile_row.addWidget(self.profile_combo, 1)
        add_btn = QPushButton("Новый")
        add_btn.setStyleSheet(button_style())
        add_btn.clicked.connect(self._new_profile)
        profile_row.addWidget(add_btn)
        rename_btn = QPushButton("Переименовать")
        rename_btn.setStyleSheet(button_style())
        rename_btn.clicked.connect(self._rename_profile)
        profile_row.addWidget(rename_btn)
        root.addLayout(profile_row)

        level_row = QHBoxLayout()
        self.character_label = QLabel()
        self.character_label.setFont(QFont("Segoe UI", 12, QFont.DemiBold))
        level_row.addWidget(self.character_label, 1)
        minus = QPushButton("−")
        plus = QPushButton("+")
        for button in (minus, plus):
            button.setFixedSize(40, 36)
            button.setStyleSheet(button_style())
        minus.clicked.connect(lambda: self._change_level(-1))
        plus.clicked.connect(lambda: self._change_level(1))
        self.level_label = QLabel()
        self.level_label.setAlignment(Qt.AlignCenter)
        self.level_label.setMinimumWidth(105)
        self.level_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        level_row.addWidget(minus)
        level_row.addWidget(self.level_label)
        level_row.addWidget(plus)
        root.addLayout(level_row)

        self.tabs = QTabWidget()
        self.gems_view = QLabel()
        self.gems_view.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.gems_view.setWordWrap(True)
        self.gems_view.setTextFormat(Qt.RichText)
        self.tree_view = QLabel()
        self.tree_view.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.tree_view.setWordWrap(True)
        self.tree_view.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.tree_view.setTextFormat(Qt.RichText)
        self.tabs.addTab(self._scroll(self.gems_view), "Камни и связки")
        self.tabs.addTab(self._scroll(self.tree_view), "Дерево")
        root.addWidget(self.tabs, 1)

        bottom = QHBoxLayout()
        self.status = QLabel()
        self.status.setWordWrap(True)
        self.status.setStyleSheet(f"color:{legacy.Style.TEXT_MUTED};")
        bottom.addWidget(self.status, 1)
        import_btn = QPushButton("Импортировать PoB")
        import_btn.setStyleSheet(button_style(True))
        import_btn.clicked.connect(self._import_pob)
        bottom.addWidget(import_btn)
        root.addLayout(bottom)
        self.reload()

    def _scroll(self, widget):
        holder = QWidget()
        layout = QVBoxLayout(holder)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.addWidget(widget)
        layout.addStretch()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(holder)
        return scroll

    def reload(self):
        active_id = self.overlay.active_profile().get("id")
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        selected = 0
        for index, profile in enumerate(self.overlay.profile_data["profiles"]):
            self.profile_combo.addItem(profile.get("name", "Персонаж"), profile.get("id"))
            if profile.get("id") == active_id:
                selected = index
        self.profile_combo.setCurrentIndex(selected)
        self.profile_combo.blockSignals(False)
        self.refresh_level()

    def refresh_level(self):
        profile = self.overlay.active_profile()
        level = clamp_level(profile.get("level", 1))
        build = profile.get("build")
        self.level_label.setText(f"Уровень {level}")
        subtitle = profile.get("name", "Персонаж")
        if build:
            details = " ".join(x for x in (build.get("class"), build.get("ascendancy")) if x)
            subtitle += f" — {details or build.get('name', 'PoB билд')}"
        self.character_label.setText(subtitle)
        self._render_gems(build, level)
        self._render_tree(build, level)

    def _render_gems(self, build, level):
        if not build:
            self.gems_view.setText("Импортируйте PoB, чтобы увидеть связки камней.")
            self.status.setText("У персонажа пока нет импортированного билда.")
            return
        stage = stage_for_level(build.get("gem_sets", []), level)
        if not stage or not stage.get("links"):
            self.gems_view.setText("В импортированном PoB не найдены активные связки камней.")
            return
        blocks = [f"<h3>{html.escape(stage.get('title', 'Связки'))}</h3>"]
        for link in stage["links"]:
            gems = []
            for gem in link.get("gems", []):
                color = "#7dd3fc" if gem.get("support") else legacy.Style.ACCENT
                gems.append(f'<span style="color:{color}">{html.escape(gem.get("name", ""))}</span>')
            blocks.append(
                f'<p><b style="color:white">{html.escape(link.get("label", "Связка"))}</b><br>'
                + " <span style='color:#777'>—</span> ".join(gems) + "</p>"
            )
        self.gems_view.setText("".join(blocks))
        self.status.setText(
            f"Показан ближайший этап камней: уровень {stage.get('level', 1)}. "
            "Уровень меняется независимо от шагов кампании."
        )

    def _render_tree(self, build, level):
        if not build:
            self.tree_view.setText("Импортируйте PoB, чтобы увидеть этапы дерева.")
            return
        stage = stage_for_level(build.get("trees", []), level)
        if not stage:
            self.tree_view.setText("В импортированном PoB не найдено дерево пассивных умений.")
            return
        nodes = stage.get("nodes", [])
        previous_candidates = [
            item for item in build.get("trees", [])
            if item is not stage and item.get("level", 1) < stage.get("level", 1)
        ]
        previous = max(previous_candidates, key=lambda x: x.get("level", 1)) if previous_candidates else None
        previous_nodes = set(previous.get("nodes", [])) if previous else set()
        added = [node for node in nodes if node not in previous_nodes]
        chips = " ".join(
            f'<span style="color:{legacy.Style.ACCENT}">{node}</span>' if node in added
            else f'<span style="color:#aaa">{node}</span>' for node in nodes
        )
        self.tree_view.setText(
            f"<h3>{html.escape(stage.get('title', 'Дерево'))}</h3>"
            f"<p>Этап уровня: <b>{stage.get('level', 1)}</b><br>"
            f"Выбрано пассивов: <b>{len(nodes)}</b><br>"
            f"Новых относительно прошлого этапа: <b style='color:{legacy.Style.ACCENT}'>{len(added)}</b></p>"
            "<p style='color:#888'>Сейчас показаны идентификаторы узлов из PoB. "
            "Визуальная подложка дерева будет подключена отдельно из данных дерева PoE 1.</p>"
            f"<p>{chips or 'Узлы отсутствуют'}</p>"
        )

    def _change_level(self, delta):
        profile = self.overlay.active_profile()
        profile["level"] = clamp_level(profile.get("level", 1) + delta)
        self.overlay.save_profiles()
        self.refresh_level()

    def _profile_changed(self, index):
        profile_id = self.profile_combo.itemData(index)
        if profile_id:
            self.overlay.switch_profile(profile_id)
            self.refresh_level()

    def _new_profile(self):
        name, ok = QInputDialog.getText(self, "Новый персонаж", "Имя персонажа:")
        if ok and name.strip():
            self.overlay.create_profile(name.strip())
            self.reload()

    def _rename_profile(self):
        profile = self.overlay.active_profile()
        name, ok = QInputDialog.getText(
            self, "Переименовать персонажа", "Новое имя:", text=profile.get("name", "")
        )
        if ok and name.strip():
            profile["name"] = name.strip()
            self.overlay.save_profiles()
            self.reload()

    def _import_pob(self):
        dialog = PobImportDialog(self)
        if dialog.exec_() != QDialog.Accepted:
            return
        try:
            build = parse_pob(dialog.source())
        except PobImportError as exc:
            QMessageBox.warning(self, "Не удалось импортировать PoB", str(exc))
            return
        profile = self.overlay.active_profile()
        profile["build"] = build
        if profile.get("level", 1) == 1 and build.get("character_level"):
            profile["level"] = clamp_level(build["character_level"])
        self.overlay.save_profiles()
        self.refresh_level()
        QMessageBox.information(
            self, "PoB импортирован",
            f"Деревьев: {len(build.get('trees', []))}\n"
            f"Наборов камней: {len(build.get('gem_sets', []))}"
        )


class Poe1Overlay(legacy.Overlay):
    def __init__(self):
        self.profile_store = Poe1ProfileStore(PROFILE_FILE)
        legacy_progress = legacy.load_json(legacy.get_progress_file(legacy.GAME_POE1), {})
        self.profile_data = self.profile_store.load(legacy_progress)
        self._profile_switching = False
        self._build_dialog = None
        super().__init__()

    def _setup_ui(self):
        super()._setup_ui()
        self.build_btn = legacy.make_icon_button(
            "build", "◆", legacy.Style.BTN_SIZE, self._open_build_progress, self.header
        )
        self.build_btn.setToolTip("Персонаж, камни и дерево PoE 1")
        header_layout = self.header.layout()
        settings_index = header_layout.indexOf(self.settings_btn)
        header_layout.insertWidget(settings_index, self.build_btn, 0, Qt.AlignVCenter)
        self.build_btn.setVisible(self.game == legacy.GAME_POE1)

    def _refresh_header(self):
        super()._refresh_header()
        if hasattr(self, "build_btn"):
            self._refresh_icon_button(self.build_btn, "build", "◆")

    def _switch_game(self, game):
        super()._switch_game(game)
        if hasattr(self, "build_btn"):
            self.build_btn.setVisible(game == legacy.GAME_POE1)
        if game != legacy.GAME_POE1 and self._build_dialog is not None:
            self._build_dialog.close()

    def active_profile(self):
        active_id = self.profile_data.get("active_profile_id")
        for profile in self.profile_data["profiles"]:
            if profile.get("id") == active_id:
                return profile
        profile = self.profile_data["profiles"][0]
        self.profile_data["active_profile_id"] = profile["id"]
        return profile

    def save_profiles(self):
        self.profile_store.save(self.profile_data)

    def create_profile(self, name):
        if self.game == legacy.GAME_POE1:
            self._save_progress()
        profile = new_profile(name)
        self.profile_data["profiles"].append(profile)
        self.profile_data["active_profile_id"] = profile["id"]
        self.save_profiles()
        self._load_profile_campaign()

    def switch_profile(self, profile_id):
        if profile_id == self.profile_data.get("active_profile_id"):
            return
        if self.game == legacy.GAME_POE1:
            self._save_progress()
        self.profile_data["active_profile_id"] = profile_id
        self.save_profiles()
        self._load_profile_campaign()

    def _load_profile_campaign(self):
        self._profile_switching = True
        try:
            self.content.reset()
            self.timer.reset()
            data = self.active_profile().get("campaign", {})
            if "steps" in data:
                self.content.set_state(data["steps"])
            if "timer" in data:
                self.timer.set_state(data["timer"])
            self._update_progress_bar()
        finally:
            self._profile_switching = False

    def _save_progress(self):
        if getattr(self, "_profile_switching", False):
            return
        if getattr(self, "game", None) != legacy.GAME_POE1:
            return super()._save_progress()
        if not hasattr(self, "content"):
            return
        self.active_profile()["campaign"] = {
            "steps": self.content.get_state(),
            "timer": self.timer.get_state(),
        }
        self.save_profiles()

    def _load_progress(self):
        if getattr(self, "game", None) != legacy.GAME_POE1:
            return super()._load_progress()
        self._load_profile_campaign()

    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = BuildProgressDialog(self)
            self._build_dialog.finished.connect(lambda _: setattr(self, "_build_dialog", None))
        self._build_dialog.reload()
        self._build_dialog.show()
        self._build_dialog.raise_()
        self._build_dialog.activateWindow()

    def closeEvent(self, event):
        if self._build_dialog is not None:
            self._build_dialog.close()
        super().closeEvent(event)


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setApplicationName(legacy.APP_NAME)
    app.setApplicationDisplayName(legacy.APP_NAME + " — PoE 1")
    legacy.ensure_cormorant_loaded()
    app.setFont(QFont("Segoe UI", 10))
    window = Poe1Overlay()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
