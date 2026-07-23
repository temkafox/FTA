"""65 слоёв MRO оверлея PoE1, сведённые из main.Overlay и башни main_poe1*/
release_poe1* в один модуль. Классы дословны; переписаны только базы в
заголовках и module-level проводка. build_dialog/v41/v50 импортируются в конце,
после определения всех классов, чтобы обратные `from actpilot.overlay import`
из модулей-источников не ловили полуготовый модуль."""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt5.QtCore import QEvent, QPoint, QPointF, QSize, Qt, QTimer
from PyQt5.QtGui import QColor, QCursor, QFont, QIcon, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import (
    QApplication, QDialog, QFrame, QHBoxLayout, QLabel, QMessageBox,
    QPushButton, QVBoxLayout, QWidget,
)

import actpilot.shared as legacy

from actpilot.hotkeys import HotkeyListener, display_hotkey, normalize_hotkey
from actpilot.messagebox import MESSAGE_STYLE
from actpilot.paths import APP_NAME, SETTINGS_FILE
from actpilot.persistence import load_json, save_json
from actpilot.regex_dialog import DEFAULT_REGEXES, RegexDialog
from actpilot.steps import (
    DEFAULT_STEPS, DEFAULT_STEPS_POE2, GAME_POE1, GAME_POE2,
    get_progress_file, get_steps_file,
)
from actpilot.style import Style
from actpilot.winapi import set_window_click_through
from actpilot.widgets import (
    ContentArea, CornerResizeHandles, DEFAULT_SETTINGS, FantasyProgressBar,
    HotkeyFooter, LayoutHintDialog, Timer, WelcomePanel, draw_nine_slice,
    load_background_pixmap, make_icon_button, scaled_ui_pixmap,
    set_widget_transparent,
)
from actpilot.shared import ensure_dirs, migrate_legacy_progress, migrate_settings
from actpilot.settings_dialog import UpdateSettingsDialog

from actpilot.builds import Poe1ProfileStore, clamp_level, new_profile
from actpilot.clientlog import class_matches
from actpilot.clientmonitor import ClientLevelMonitor
from actpilot.minipanels import MiniPassiveRoute
from actpilot.editor import ManualBuildEditor
from actpilot.minipanels import MiniGemLinksV5 as MiniGemLinks

# Живой рантайм-патч app.py (settings_release.Poe1SettingsDialog = UpdateSettingsDialog)
# материализован: _settings живёт здесь, поэтому имя резолвится в этом неймспейсе.
Poe1SettingsDialog = UpdateSettingsDialog

PROFILE_FILE = legacy.DATA_DIR / "poe1_characters.json"

COMPACT_BASE = {
    "TIMER_SIZE": 27,
    "HEADER_H": 54,
    "LOGO_HEIGHT": 35,
    "BTN_SIZE": 28,
}


def build_tree_icon(size=22):
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    gold = QColor("#c9a35a")
    painter.setPen(QPen(gold, 1.5))
    points = [QPointF(size * .50, size * .22), QPointF(size * .25, size * .70), QPointF(size * .75, size * .70)]
    painter.drawLine(points[0], points[1])
    painter.drawLine(points[0], points[2])
    painter.drawLine(points[1], points[2])
    painter.setBrush(QColor("#18150f"))
    for point in points:
        painter.drawEllipse(point, 2.8, 2.8)
    painter.end()
    return QIcon(pixmap)


def _install_compact_metrics():
    legacy._STYLE_NUMERIC_BASE.update(COMPACT_BASE)


class Overlay(QWidget):
    def __init__(self):
        super().__init__()
        
        ensure_dirs()
        migrate_legacy_progress()
        self.settings = load_json(SETTINGS_FILE, DEFAULT_SETTINGS)
        if migrate_settings(self.settings):
            save_json(SETTINGS_FILE, self.settings)
        self.settings["hotkey"] = normalize_hotkey(
            self.settings.get("hotkey", DEFAULT_SETTINGS["hotkey"])
        )
        self.settings["layout_hotkey"] = normalize_hotkey(
            self.settings.get("layout_hotkey", DEFAULT_SETTINGS["layout_hotkey"])
        )
        self._ui_scale = float(self.settings.get("ui_scale", DEFAULT_SETTINGS["ui_scale"]))
        Style.set_ui_scale(self._ui_scale)
        self.game = self.settings.get("game", DEFAULT_SETTINGS["game"])
        self._load_steps_data()
        
        self._collapsed = False
        self._welcome_dismissed_session = False
        size = self.settings.get("size", DEFAULT_SETTINGS["size"])
        self._expanded_size = QSize(size["width"], size["height"])
        self._resizing = False
        self._resize_edge = None
        self._drag_pos = None
        self._bg_pixmap = load_background_pixmap()
        self._has_bg = not self._bg_pixmap.isNull()
        
        self.hotkey = HotkeyListener(self.settings["hotkey"])
        self.previous_hotkey = HotkeyListener(
            self.settings.get("previous_hotkey", DEFAULT_SETTINGS["previous_hotkey"])
        )
        self.layout_hotkey = HotkeyListener(
            self.settings.get("layout_hotkey", DEFAULT_SETTINGS["layout_hotkey"])
        )
        self.regex_hotkey = HotkeyListener(
            self.settings.get("regex_hotkey", DEFAULT_SETTINGS["regex_hotkey"])
        )
        self._layout_dialog = None
        self._regex_dialog = None
        self._regex_restore_state = None
        
        self._setup_ui()
        self._setup_hotkey()
        self._load_progress()
    
    def _load_steps_data(self):
        steps_file = get_steps_file(self.game)
        default = DEFAULT_STEPS_POE2 if self.game == GAME_POE2 else DEFAULT_STEPS
        self.steps_data = load_json(steps_file, default)
    
    def _switch_game(self, game: str):
        self.game = game
        self._load_steps_data()
        self.content.load(self.steps_data)
        self.timer.reset()
        self._load_progress()
        self._start_hotkey()
        
    def _setup_ui(self):
        self.setWindowTitle(APP_NAME)
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setMouseTracking(True)
        self.setMinimumSize(max(150, int(280 * Style.ui_scale())), max(100, int(180 * Style.ui_scale())))
        
        size = self.settings.get("size", DEFAULT_SETTINGS["size"])
        self._expanded_size = QSize(size["width"], size["height"])
        self.resize(self._expanded_size)
        
        screen = QApplication.primaryScreen().geometry()
        pos = self.settings.get("position", DEFAULT_SETTINGS["position"])
        x = pos["x"] if pos["x"] >= 0 else screen.width() - self.width() - 40
        self.move(x, pos["y"])
        
        if self._has_bg:
            self.setAttribute(Qt.WA_TranslucentBackground, True)
            self.setAttribute(Qt.WA_NoSystemBackground, True)
            self.setStyleSheet("""
                QWidget#main {
                    background: transparent;
                    border: none;
                }
                QWidget {
                    background: transparent;
                }
            """)
        else:
            self.setStyleSheet(f"""
                QWidget#main {{
                    background: {Style.BG};
                    border-radius: {Style.RAD_L}px;
                    border: 1px solid {Style.BORDER};
                }}
            """)
        self.setObjectName("main")
        set_widget_transparent(self)
        
        self._panel_margins = Style.panel_margins(self._has_bg)
        pad_x, panel_top, pad_right, panel_bottom = self._panel_margins

        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(pad_x, panel_top, pad_right, panel_bottom)
        self._main_layout.setSpacing(0)
        layout = self._main_layout
        
        # Header
        self.header = QFrame()
        self.header.setFixedHeight(Style.HEADER_H)
        self.header.setStyleSheet("background: transparent;")
        self.header.setMouseTracking(True)
        
        h_layout = QHBoxLayout(self.header)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(Style.PAD_S)
        
        self.logo_label = None
        logo = scaled_ui_pixmap("logo", height=Style.LOGO_HEIGHT)
        if not logo.isNull():
            self.logo_label = QLabel()
            self.logo_label.setPixmap(logo)
            self.logo_label.setStyleSheet("background: transparent;")
            set_widget_transparent(self.logo_label)
            h_layout.addWidget(self.logo_label, 0, Qt.AlignVCenter)
        
        h_layout.addStretch()
        
        self.collapse_btn = make_icon_button(
            "collapse", "−", Style.BTN_SIZE, self._toggle, self.header
        )
        align = Qt.AlignVCenter
        h_layout.addWidget(self.collapse_btn, 0, align)
        self.settings_btn = make_icon_button(
            "settings", "⚙", Style.BTN_SIZE, self._settings, self.header
        )
        self.close_btn = make_icon_button(
            "close", "×", Style.BTN_SIZE, self.close, self.header
        )
        h_layout.addWidget(self.settings_btn, 0, align)
        h_layout.addWidget(self.close_btn, 0, align)
        
        layout.addWidget(self.header)
        
        # Body
        self.body = QFrame()
        self.body.setStyleSheet("background: transparent;")
        self.body.setMouseTracking(True)
        
        body_layout = QVBoxLayout(self.body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)
        
        self.timer = Timer()
        body_layout.addWidget(self.timer)
        body_layout.addSpacing(Style.PAD_XS)

        self.progress_bar = FantasyProgressBar()
        body_layout.addWidget(self.progress_bar)
        body_layout.addSpacing(Style.PAD_S)

        self.welcome_panel = WelcomePanel(self.settings)
        self.welcome_panel.dismissed.connect(self._on_welcome_dismissed)
        body_layout.addWidget(self.welcome_panel, 1)
        
        self.content = ContentArea()
        self.content.set_timer(self.timer)
        self.content.load(self.steps_data)
        self.content.set_show_splits(
            self.settings.get("show_step_splits", DEFAULT_SETTINGS["show_step_splits"]))
        self.content.progress_changed.connect(self._update_progress_bar)
        self.content.progress_changed.connect(self._save_progress)
        self.content.first_step_started.connect(self._on_first_step)
        self.content.active_step_changed.connect(self._on_active_step_changed)
        body_layout.addWidget(self.content, 1)

        self.hotkey_footer = HotkeyFooter()
        self.hotkey_footer.setObjectName("hotkeyFooter")
        self.hotkey_footer.setStyleSheet(
            "color:#a9a08e; background:transparent; border:0; font-size:8px; padding:3px 1px 0 1px;"
        )
        body_layout.addWidget(self.hotkey_footer)
        self._refresh_hotkey_footer()

        self._apply_welcome_visibility()
        
        layout.addWidget(self.body, 1)
        
        min_w = max(150, int(280 * Style.ui_scale()))
        min_h = max(100, int(180 * Style.ui_scale()))
        self._resize_handles = CornerResizeHandles(
            self,
            min_w,
            min_h,
            on_resize_end=self._on_corner_resize_end,
            collapsed_width_only=self._collapsed,
        )
        
        self._apply_transparent_layers()
        self._update_opacity()
        self._update_progress_bar()

        self._click_through_enabled = False
        self._click_through_timer = QTimer(self)
        self._click_through_timer.setInterval(40)
        self._click_through_timer.timeout.connect(self._sync_click_through_state)
    
    def _apply_transparent_layers(self):
        for widget in (
            self.header,
            self.body,
            self.timer,
            self.progress_bar,
            self.content,
            self.content.viewport(),
            self.content.steps_widget,
            self.welcome_panel,
        ):
            set_widget_transparent(widget)
        for w in self.welcome_panel.findChildren(QWidget):
            set_widget_transparent(w)
        if hasattr(self, "_resize_handles"):
            for w in self._resize_handles.handles():
                set_widget_transparent(w)
        for label in self.timer.findChildren(QLabel):
            set_widget_transparent(label)
        self.timer.set_control_button_theme(filled=not self._has_bg)
    
    def _update_progress_bar(self):
        if self.content.isVisible():
            self.progress_bar.setValue(self.content.progress_percent())

    def _apply_welcome_visibility(self):
        show = (
            bool(self.settings.get("show_welcome", True))
            and not self._collapsed
            and not self._welcome_dismissed_session
        )
        self.welcome_panel.setVisible(show)
        self.timer.setVisible(not show)
        self.progress_bar.setVisible(not show)
        self.content.setVisible(not show)

    def _on_welcome_dismissed(self, dont_show_again: bool):
        self._welcome_dismissed_session = True
        if dont_show_again:
            self.settings["show_welcome"] = False
            save_json(SETTINGS_FILE, self.settings)
        self._apply_welcome_visibility()
        self._update_progress_bar()
    
    def _apply_panel_margins(self):
        self._panel_margins = Style.panel_margins(self._has_bg)
        pad_x, panel_top, pad_right, panel_bottom = self._panel_margins
        self._main_layout.setContentsMargins(pad_x, panel_top, pad_right, panel_bottom)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        if self._has_bg:
            borders = (
                Style.BG_SLICE_LEFT,
                Style.BG_SLICE_TOP,
                Style.BG_SLICE_RIGHT,
                Style.BG_SLICE_BOTTOM,
            )
            draw_nine_slice(painter, self._bg_pixmap, self.rect(), borders)
        else:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(Style.BG))
            painter.drawRoundedRect(self.rect(), Style.RAD_L, Style.RAD_L)
        painter.end()
        super().paintEvent(event)
    
    def _update_opacity(self):
        opacity = self.settings.get("opacity", 0.95)
        self.setWindowOpacity(opacity)

    def _on_corner_resize_end(self, size: QSize):
        if not self._collapsed:
            self._expanded_size = size

    def _reposition_resize_handles(self):
        if hasattr(self, "_resize_handles"):
            self._resize_handles.reposition()

    def _refresh_icon_button(self, btn: QPushButton, asset: str, fallback: str):
        size = Style.BTN_SIZE
        btn.setFixedSize(size, size)
        if asset == "collapse":
            btn.setIcon(QIcon())
            btn.setText("+" if self._collapsed else "−")
            btn.setFont(QFont("Segoe UI", max(10, int(round(13 * Style.ui_scale())))))
            btn.setStyleSheet("""
                QPushButton { background:transparent; color:#c9a35a; border:0; padding:0; }
                QPushButton:hover { background:rgba(122,83,30,.18); border-radius:6px; }
                QPushButton:pressed { background:rgba(172,124,47,.24); }
            """)
            return
        icon = scaled_ui_pixmap(asset, size, size)
        if not icon.isNull():
            btn.setIcon(QIcon(icon))
            btn.setIconSize(icon.size())
            btn.setText("")
        else:
            btn.setIcon(QIcon())
            btn.setText(fallback)

    def _refresh_header(self):
        if self.logo_label is not None:
            logo = scaled_ui_pixmap("logo", height=Style.LOGO_HEIGHT)
            if not logo.isNull():
                self.logo_label.setPixmap(logo)
        self._refresh_icon_button(self.collapse_btn, "collapse", "−")
        self._refresh_icon_button(self.settings_btn, "settings", "⚙")
        self._refresh_icon_button(self.close_btn, "close", "×")
        self.header.layout().setSpacing(Style.PAD_S)

    def _apply_ui_scale(self, old_scale: float, new_scale: float):
        if abs(old_scale - new_scale) < 0.001:
            return
        Style.set_ui_scale(new_scale)
        ratio = new_scale / old_scale if old_scale > 0 else new_scale

        self._apply_panel_margins()

        if self._collapsed:
            w = max(150, int(self.width() * ratio))
            self.setFixedSize(w, Style.collapsed_height(self._has_bg))
        else:
            w = max(150, int(self._expanded_size.width() * ratio))
            h = max(100, int(self._expanded_size.height() * ratio))
            self._expanded_size = QSize(w, h)
            self.resize(self._expanded_size)

        self.setMinimumSize(max(150, int(280 * new_scale)), max(100, int(180 * new_scale)))
        self.header.setFixedHeight(Style.HEADER_H)
        self._refresh_header()
        self.timer.refresh_scale()
        self.progress_bar.refresh_scale()
        for group in self.content.groups:
            group.refresh_scale()
        self._reposition_resize_handles()
        self.update()

    def _interactive_widgets(self):
        widgets = [
            self.collapse_btn,
            self.settings_btn,
            self.close_btn,
            self.timer.btn,
        ]
        if hasattr(self, "_resize_handles"):
            widgets.extend(self._resize_handles.handles())
        return widgets

    def _hit_test_interactive(self, global_pos: QPoint) -> bool:
        # Click-through must never swallow the title bar: it is the permanent
        # grab handle for moving the overlay, including in passthrough mode.
        if self.header is not None and self.header.isVisible():
            header_top_left = self.header.mapToGlobal(QPoint(0, 0))
            if QRect(header_top_left, self.header.size()).contains(global_pos):
                return True
        if self.welcome_panel.isVisible():
            top_left = self.welcome_panel.mapToGlobal(QPoint(0, 0))
            if QRect(top_left, self.welcome_panel.size()).contains(global_pos):
                return True
        pad = 6
        for widget in self._interactive_widgets():
            if widget is None or not widget.isVisible() or not widget.isEnabled():
                continue
            top_left = widget.mapToGlobal(QPoint(0, 0))
            hit = QRect(
                top_left.x() - pad,
                top_left.y() - pad,
                widget.width() + pad * 2,
                widget.height() + pad * 2,
            )
            if hit.contains(global_pos):
                return True
        return False

    def _sync_click_through_state(self):
        if not self._click_through_enabled:
            set_window_click_through(self, False)
            return
        pos = QCursor.pos()
        over_overlay = self.frameGeometry().contains(pos)
        passthrough = not over_overlay or not self._hit_test_interactive(pos)
        set_window_click_through(self, passthrough)

    def _apply_click_through_mode(self):
        self._click_through_enabled = bool(self.settings.get("click_through", False))
        if self._click_through_enabled and sys.platform == "win32":
            self._click_through_timer.start()
            self._sync_click_through_state()
        else:
            self._click_through_timer.stop()
            set_window_click_through(self, False)
        if self._layout_dialog is not None and self._layout_dialog.isVisible():
            self._layout_dialog._apply_click_through_mode()

    def showEvent(self, event):
        super().showEvent(event)
        self._apply_click_through_mode()
        if not getattr(self, "_hotkey_started", False):
            self._hotkey_started = True
            QTimer.singleShot(0, self._start_hotkey)

    def _setup_hotkey(self):
        self._previous_combo_active = False
        self.hotkey.triggered.connect(self._on_next_hotkey)
        self.previous_hotkey.triggered.connect(self._on_previous_hotkey)
        self.layout_hotkey.triggered.connect(self._toggle_layout_hint)
        self.regex_hotkey.triggered.connect(self._toggle_regex_dialog)
        for listener, key in (
            (self.hotkey, "hotkey"),
            (self.previous_hotkey, "previous_hotkey"),
            (self.layout_hotkey, "layout_hotkey"),
            (self.regex_hotkey, "regex_hotkey"),
        ):
            listener.failed.connect(
                lambda error, key=key: self._notify_hotkey_error(
                    self.settings.get(key, DEFAULT_SETTINGS.get(key, "")), error
                )
            )

    def _notify_hotkey_error(self, hotkey: str, error: str):
        box = getattr(self, "_hotkey_error_box", None)
        if box is None:
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Warning)
            box.setWindowTitle("Горячие клавиши")
            box.setWindowModality(Qt.NonModal)
            box.setStyleSheet(MESSAGE_STYLE)
            self._hotkey_error_box = box
        elif box.isVisible():
            return
        box.setText(
            f"Не удалось включить горячую клавишу {display_hotkey(hotkey)}.\n"
            f"{error}\nИзменить её можно в настройках (⚙)."
        )
        box.show()

    def _on_previous_hotkey(self):
        self._previous_combo_active = True
        self.content.previous_current()
        QTimer.singleShot(120, lambda: setattr(self, "_previous_combo_active", False))

    def _on_next_hotkey(self):
        # Ctrl+F3 can also be observed by the plain F3 listener. Delay the
        # plain action briefly so the more specific shortcut can suppress it.
        QTimer.singleShot(
            45,
            lambda: None if self._previous_combo_active else self.content.complete_current(),
        )

    def _start_hotkey(self):
        self.hotkey.restart(self.settings["hotkey"])
        self.previous_hotkey.restart(
            self.settings.get("previous_hotkey", DEFAULT_SETTINGS["previous_hotkey"])
        )
        self.regex_hotkey.restart(
            self.settings.get("regex_hotkey", DEFAULT_SETTINGS["regex_hotkey"])
        )
        if self.game == GAME_POE2:
            self.layout_hotkey.restart(
                self.settings.get("layout_hotkey", DEFAULT_SETTINGS["layout_hotkey"])
            )
        else:
            self.layout_hotkey.stop()
        self._refresh_hotkey_footer()

    def _save_regexes(self, entries):
        self.settings["regexes"] = entries
        save_json(SETTINGS_FILE, self.settings)

    def _toggle_regex_dialog(self):
        if self._regex_dialog is not None and self._regex_dialog.isVisible():
            self._regex_dialog.hide()
            return
        if self._regex_dialog is None:
            self._regex_dialog = RegexDialog(
                self.settings.get("regexes", DEFAULT_REGEXES), self._save_regexes, None
            )
            self._regex_dialog.hidden.connect(self._restore_after_regex)
        self._regex_restore_state = {
            "overlay": self.isVisible(),
            "layout": bool(self._layout_dialog is not None and self._layout_dialog.isVisible()),
            "build": bool(
                getattr(self, "_build_dialog", None) is not None
                and self._build_dialog.isVisible()
            ),
        }
        if self._regex_restore_state["layout"]:
            self._layout_dialog.hide()
        if self._regex_restore_state["build"]:
            self._build_dialog.hide()
        if self._regex_restore_state["overlay"]:
            self.hide()
        screen = QApplication.primaryScreen().availableGeometry()
        self._regex_dialog.move(
            screen.center().x() - self._regex_dialog.width() // 2,
            screen.center().y() - self._regex_dialog.height() // 2,
        )
        self._regex_dialog.show()
        self._regex_dialog.raise_()
        self._regex_dialog.activateWindow()

    def _restore_after_regex(self):
        state = self._regex_restore_state
        self._regex_restore_state = None
        if not state:
            return
        if state["overlay"]:
            self.show()
            self.raise_()
        if state["layout"] and self._layout_dialog is not None:
            self._layout_dialog.show()
            self._layout_dialog.raise_()
        if state["build"] and getattr(self, "_build_dialog", None) is not None:
            self._build_dialog.show()
            self._build_dialog.raise_()

    def _refresh_hotkey_footer(self):
        if not hasattr(self, "hotkey_footer"):
            return
        show = display_hotkey
        def item(key, label):
            return f"<span style='color:#629d6c;font-weight:600'>{key}</span>&nbsp; {label}"
        self.hotkey_footer.set_full_text("&nbsp; · &nbsp;".join((
            item(show(self.settings.get("hotkey", DEFAULT_SETTINGS["hotkey"])), "След. шаг"),
            item(show(self.settings.get("previous_hotkey", DEFAULT_SETTINGS["previous_hotkey"])), "Пред. шаг"),
            item(show(self.settings.get("layout_hotkey", DEFAULT_SETTINGS["layout_hotkey"])), "Мини-панель"),
            item(show(self.settings.get("regex_hotkey", DEFAULT_SETTINGS["regex_hotkey"])), "Регэкспы"),
        )))
        self.hotkey_footer.setVisible(bool(self.settings.get("show_hotkey_hints", True)))

    def _close_layout_dialog(self):
        if self._layout_dialog is not None:
            self._layout_dialog._save_layout_size()
            self._layout_dialog._save_layout_position()
            self._layout_dialog._click_through_timer.stop()
            set_window_click_through(self._layout_dialog, False)
            self._layout_dialog.close()
            self._layout_dialog = None

    def _position_layout_dialog(self):
        if self._layout_dialog is None:
            return
        dlg = self._layout_dialog
        if dlg._saved_position() is not None:
            dlg.apply_saved_position()
            return
        screen = QApplication.primaryScreen().availableGeometry()
        x = self.x() + self.width() + 16
        y = self.y()
        if x + dlg.width() > screen.right():
            x = max(screen.left(), self.x() - dlg.width() - 16)
        if y + dlg.height() > screen.bottom():
            y = max(screen.top(), screen.bottom() - dlg.height() - 8)
        dlg.move(dlg._clamp_position(QPoint(x, y)))

    def _refresh_layout_hint(self):
        if self.game != GAME_POE2:
            return
        first_open = self._layout_dialog is None
        if first_open:
            self._layout_dialog = LayoutHintDialog(self)
        was_visible = self._layout_dialog.isVisible()
        act, step_index, step_text = self.content.get_active_step_info()
        self._layout_dialog.set_opacity(1.0)
        self._layout_dialog.show_for_step(act, step_index, step_text)
        if first_open or not was_visible:
            self._position_layout_dialog()

    def _toggle_layout_hint(self):
        if self.game != GAME_POE2:
            return
        if self._layout_dialog is not None and self._layout_dialog.isVisible():
            self._close_layout_dialog()
            return
        self._refresh_layout_hint()
        if self._layout_dialog is not None:
            self._layout_dialog.show()
            self._position_layout_dialog()
            self._layout_dialog._apply_click_through_mode()

    def _on_active_step_changed(self):
        if (
            self.game == GAME_POE2
            and self._layout_dialog is not None
            and self._layout_dialog.isVisible()
        ):
            self._refresh_layout_hint()
            self._layout_dialog.scroll_to_top()
    
    def _on_first_step(self):
        if not self.timer._running:
            self.timer.start()
    
    def _collapsed_height(self) -> int:
        return Style.collapsed_height(self._has_bg)

    def _drag_zone_height(self) -> int:
        if self._collapsed:
            return self._collapsed_height()
        _, top, _, _ = self._panel_margins
        return top + Style.HEADER_H

    def _toggle(self):
        self._collapsed = not self._collapsed
        self.body.setVisible(not self._collapsed)
        if hasattr(self, "_resize_handles"):
            self._resize_handles.set_collapsed_mode(self._collapsed)
            self._resize_handles.setVisible(True)
        if self._collapsed:
            self.welcome_panel.setVisible(False)
            self._expanded_size = self.size()
            self.setFixedSize(self.width(), self._collapsed_height())
            if self.collapse_btn.text():
                self.collapse_btn.setText("+")
        else:
            self.setMinimumSize(
                max(150, int(280 * Style.ui_scale())),
                max(100, int(180 * Style.ui_scale())),
            )
            self.setMaximumSize(16777215, 16777215)
            self.resize(self._expanded_size)
            self.header.setFixedHeight(Style.HEADER_H)
            if self.collapse_btn.text():
                self.collapse_btn.setText("−")
            self._apply_welcome_visibility()
        self._refresh_icon_button(self.collapse_btn, "collapse", "−")
        self.update()
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reposition_resize_handles()
        if self._has_bg:
            self.update()
    
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            edge = self._get_edge(e.pos())
            if edge:
                self._resizing = True
                self._resize_edge = edge
                self._resize_start = e.globalPos()
                self._resize_geom = self.geometry()
            elif e.pos().y() < self._drag_zone_height():
                self._drag_pos = e.globalPos() - self.frameGeometry().topLeft()
    
    def mouseMoveEvent(self, e):
        if self._resizing:
            self._do_resize(e.globalPos())
        elif self._drag_pos:
            self.move(e.globalPos() - self._drag_pos)
        else:
            edge = self._get_edge(e.pos())
            if edge:
                cursors = {
                    "left": Qt.SizeHorCursor, "right": Qt.SizeHorCursor,
                    "top": Qt.SizeVerCursor, "bottom": Qt.SizeVerCursor,
                    "top-left": Qt.SizeFDiagCursor, "bottom-right": Qt.SizeFDiagCursor,
                    "top-right": Qt.SizeBDiagCursor, "bottom-left": Qt.SizeBDiagCursor,
                }
                self.setCursor(cursors.get(edge, Qt.ArrowCursor))
            else:
                self.setCursor(Qt.ArrowCursor)
    
    def mouseReleaseEvent(self, e):
        self._resizing = False
        self._resize_edge = None
        self._drag_pos = None
        self.setCursor(Qt.ArrowCursor)
    
    def _get_edge(self, pos):
        m = 8
        x, y, w, h = pos.x(), pos.y(), self.width(), self.height()
        l, r, t, b = x < m, x > w - m, y < m, y > h - m

        if self._collapsed:
            if l:
                return "left"
            if r:
                return "right"
            return None
        
        if b and r: return "bottom-right"
        if b and l: return "bottom-left"
        if t and r: return "top-right"
        if t and l: return "top-left"
        if l: return "left"
        if r: return "right"
        if t: return "top"
        if b: return "bottom"
        return None
    
    def _do_resize(self, pos):
        diff = pos - self._resize_start
        g = self._resize_geom
        x, y, w, h = g.x(), g.y(), g.width(), g.height()
        min_w = max(150, int(280 * Style.ui_scale()))
        min_h = max(100, int(180 * Style.ui_scale()))

        if self._collapsed:
            min_w = max(120, int(220 * Style.ui_scale()))
            if "right" in self._resize_edge:
                w = max(min_w, g.width() + diff.x())
            if "left" in self._resize_edge:
                d = min(diff.x(), g.width() - min_w)
                x, w = g.x() + d, g.width() - d
            self.setFixedSize(w, Style.collapsed_height(self._has_bg))
            self.setGeometry(x, y, w, h)
            return
        
        if "right" in self._resize_edge:
            w = max(min_w, g.width() + diff.x())
        if "left" in self._resize_edge:
            d = min(diff.x(), g.width() - min_w)
            x, w = g.x() + d, g.width() - d
        if "bottom" in self._resize_edge:
            h = max(min_h, g.height() + diff.y())
        if "top" in self._resize_edge:
            d = min(diff.y(), g.height() - min_h)
            y, h = g.y() + d, g.height() - d
        
        self.setGeometry(x, y, w, h)
    
    def _save_progress(self):
        save_json(get_progress_file(self.game), {
            "steps": self.content.get_state(),
            "timer": self.timer.get_state()
        })
    
    def _load_progress(self):
        data = load_json(get_progress_file(self.game), {})
        if "steps" in data:
            self.content.set_state(data["steps"])
        if "timer" in data:
            self.timer.set_state(data["timer"])
        self._update_progress_bar()

    def _reload_steps(self):
        """Перечитывает шаги после правки в редакторе, сохраняя прогресс.

        set_state переносит отметки по тексту шага, поэтому вставка/удаление
        шагов не сбивает уже пройденное. Таймер не трогаем."""
        state = self.content.get_state()
        self._load_steps_data()
        self.content.load(self.steps_data)
        self.content.set_state(state)
        self._update_progress_bar()
        self._save_progress()

    def closeEvent(self, e):
        self._click_through_timer.stop()
        set_window_click_through(self, False)
        self._save_progress()
        self.settings["position"] = {"x": self.x(), "y": self.y()}
        if not self._collapsed:
            self._expanded_size = self.size()
        self.settings["size"] = {
            "width": self._expanded_size.width(),
            "height": self._expanded_size.height(),
        }
        save_json(SETTINGS_FILE, self.settings)
        self.hotkey.stop()
        self.previous_hotkey.stop()
        self.layout_hotkey.stop()
        self.regex_hotkey.stop()
        if self._regex_dialog is not None:
            self._regex_restore_state = None
            self._regex_dialog.close()
        self._close_layout_dialog()
        if hasattr(self, "tray"):
            self.tray.hide()
        e.accept()
        QApplication.quit()


class Poe1Overlay(Overlay):
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


class EnhancedPoe1Overlay(Poe1Overlay):
    def _interactive_widgets(self):
        widgets = super()._interactive_widgets()
        if hasattr(self, "build_btn") and self.build_btn not in widgets:
            widgets.append(self.build_btn)
        return widgets

    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = EnhancedBuildProgressDialog(self)
            self._build_dialog.finished.connect(
                lambda _: setattr(self, "_build_dialog", None)
            )
        self._build_dialog.reload()
        self._build_dialog.show()
        self._build_dialog.raise_()
        self._build_dialog.activateWindow()


class TargetPoe1Overlay(EnhancedPoe1Overlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = TargetBuildProgressDialog(self)
            self._build_dialog.finished.connect(
                lambda _: setattr(self, "_build_dialog", None)
            )
        self._build_dialog.reload()
        self._build_dialog.show()
        self._build_dialog.raise_()
        self._build_dialog.activateWindow()


class PerLevelOverlay(TargetPoe1Overlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = PerLevelBuildDialog(self)
            self._build_dialog.finished.connect(
                lambda _: setattr(self, "_build_dialog", None)
            )
        self._build_dialog.reload()
        self._build_dialog.show()
        self._build_dialog.raise_()
        self._build_dialog.activateWindow()


class CorrectedOverlay(PerLevelOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = CorrectedBuildDialog(self)
            self._build_dialog.finished.connect(
                lambda _: setattr(self, "_build_dialog", None)
            )
        self._build_dialog.reload()
        self._build_dialog.show()
        self._build_dialog.raise_()
        self._build_dialog.activateWindow()


class FinalOverlay(CorrectedOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = FinalBuildDialog(self)
            self._build_dialog.finished.connect(
                lambda _: setattr(self, "_build_dialog", None)
            )
        self._build_dialog.reload()
        self._build_dialog.show()
        self._build_dialog.raise_()
        self._build_dialog.activateWindow()


class ReleaseOverlay(FinalOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = ReleaseBuildDialog(self)
            self._build_dialog.finished.connect(
                lambda _: setattr(self, "_build_dialog", None)
            )
        self._build_dialog.reload()
        self._build_dialog.show()
        self._build_dialog.raise_()
        self._build_dialog.activateWindow()


class CleanOverlay(ReleaseOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = CleanBuildDialog(self)
            self._build_dialog.finished.connect(
                lambda _: setattr(self, "_build_dialog", None)
            )
        self._build_dialog.reload()
        self._build_dialog.show()
        self._build_dialog.raise_()
        self._build_dialog.activateWindow()


class FullStageOverlay(CleanOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = FullStageBuildDialog(self)
            self._build_dialog.finished.connect(
                lambda _: setattr(self, "_build_dialog", None)
            )
        self._build_dialog.reload()
        self._build_dialog.show()
        self._build_dialog.raise_()
        self._build_dialog.activateWindow()


class MasteryOverlay(FullStageOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = MasteryBuildDialog(self)
            self._build_dialog.finished.connect(
                lambda _: setattr(self, "_build_dialog", None)
            )
        self._build_dialog.reload()
        self._build_dialog.show()
        self._build_dialog.raise_()
        self._build_dialog.activateWindow()


class OrbitalOverlay(MasteryOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = OrbitalBuildDialog(self)
            self._build_dialog.finished.connect(
                lambda _: setattr(self, "_build_dialog", None)
            )
        self._build_dialog.reload()
        self._build_dialog.show()
        self._build_dialog.raise_()
        self._build_dialog.activateWindow()


class RouteOverlay(OrbitalOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = RouteBuildDialog(self)
            self._build_dialog.finished.connect(lambda _: setattr(self, "_build_dialog", None))
        self._build_dialog.reload()
        self._build_dialog.show()
        self._build_dialog.raise_()
        self._build_dialog.activateWindow()


class CombinedOverlay(RouteOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = CombinedBuildDialog(self)
            self._build_dialog.finished.connect(
                lambda _: setattr(self, "_build_dialog", None)
            )
        self._build_dialog.reload()
        self._build_dialog.show()
        self._build_dialog.raise_()
        self._build_dialog.activateWindow()


class ProgressionOverlay(CombinedOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = ProgressionBuildDialog(self)
            self._build_dialog.finished.connect(
                lambda _: setattr(self, "_build_dialog", None)
            )
        self._build_dialog.reload()
        self._build_dialog.show()
        self._build_dialog.raise_()
        self._build_dialog.activateWindow()


class FixedProgressionOverlay(ProgressionOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = FixedProgressionBuildDialog(self)
            self._build_dialog.finished.connect(
                lambda _: setattr(self, "_build_dialog", None)
            )
        self._build_dialog.reload()
        self._build_dialog.show()
        self._build_dialog.raise_()
        self._build_dialog.activateWindow()


class ScaledGemOverlay(FixedProgressionOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = ScaledGemBuildDialog(self)
            self._build_dialog.finished.connect(
                lambda _: setattr(self, "_build_dialog", None)
            )
        self._build_dialog.reload()
        self._build_dialog.show()
        self._build_dialog.raise_()
        self._build_dialog.activateWindow()


class LevelMappedOverlay(ScaledGemOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = LevelMappedBuildDialog(self)
            self._build_dialog.finished.connect(
                lambda _: setattr(self, "_build_dialog", None)
            )
        self._build_dialog.reload()
        self._build_dialog.show()
        self._build_dialog.raise_()
        self._build_dialog.activateWindow()


class FinalLevelMappedOverlay(LevelMappedOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = FinalLevelMappedBuildDialog(self)
            self._build_dialog.finished.connect(
                lambda _: setattr(self, "_build_dialog", None)
            )
        self._build_dialog.reload()
        self._build_dialog.show()
        self._build_dialog.raise_()
        self._build_dialog.activateWindow()


class ImmediateFocusOverlay(FinalLevelMappedOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = ImmediateFocusBuildDialog(self)
            self._build_dialog.finished.connect(
                lambda _: setattr(self, "_build_dialog", None)
            )
        self._build_dialog.reload()
        self._build_dialog.show()
        self._build_dialog.raise_()
        self._build_dialog.activateWindow()


class StrictProgressionOverlay(ImmediateFocusOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = StrictProgressionBuildDialog(self)
            self._build_dialog.finished.connect(
                lambda _: setattr(self, "_build_dialog", None)
            )
        self._build_dialog.reload()
        self._build_dialog.show()
        self._build_dialog.raise_()
        self._build_dialog.activateWindow()


class QuestAwareOverlay(StrictProgressionOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = QuestAwareBuildDialog(self)
            self._build_dialog.finished.connect(
                lambda _: setattr(self, "_build_dialog", None)
            )
        self._build_dialog.reload()
        self._build_dialog.show()
        self._build_dialog.raise_()
        self._build_dialog.activateWindow()


class BookOnlyOverlay(QuestAwareOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = BookOnlyBuildDialog(self)
            self._build_dialog.finished.connect(
                lambda _: setattr(self, "_build_dialog", None)
            )
        self._build_dialog.reload()
        self._build_dialog.show()
        self._build_dialog.raise_()
        self._build_dialog.activateWindow()


class ContinuousPassiveOverlay(BookOnlyOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = ContinuousPassiveBuildDialog(self)
            self._build_dialog.finished.connect(
                lambda _: setattr(self, "_build_dialog", None)
            )
        self._build_dialog.reload()
        self._build_dialog.show()
        self._build_dialog.raise_()
        self._build_dialog.activateWindow()


class SemanticPassiveOverlay(ContinuousPassiveOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = SemanticPassiveBuildDialog(self)
            self._build_dialog.finished.connect(
                lambda _: setattr(self, "_build_dialog", None)
            )
        self._build_dialog.reload()
        self._build_dialog.show()
        self._build_dialog.raise_()
        self._build_dialog.activateWindow()


class CorrectedSemanticOverlay(SemanticPassiveOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = CorrectedSemanticBuildDialog(self)
            self._build_dialog.finished.connect(
                lambda _: setattr(self, "_build_dialog", None)
            )
        self._build_dialog.reload()
        self._build_dialog.show()
        self._build_dialog.raise_()
        self._build_dialog.activateWindow()


class CleanArtworkOverlay(CorrectedSemanticOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = CleanArtworkBuildDialog(self)
            self._build_dialog.finished.connect(
                lambda _: setattr(self, "_build_dialog", None)
            )
        self._build_dialog.reload()
        self._build_dialog.show()
        self._build_dialog.raise_()
        self._build_dialog.activateWindow()


class SocketedGemOverlay(CleanArtworkOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = SocketedGemBuildDialog(self)
            self._build_dialog.finished.connect(
                lambda _: setattr(self, "_build_dialog", None)
            )
        self._build_dialog.reload()
        self._build_dialog.show()
        self._build_dialog.raise_()
        self._build_dialog.activateWindow()


class AscendancyOverlay(SocketedGemOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = AscendancyBuildDialog(self)
            self._build_dialog.finished.connect(
                lambda _: setattr(self, "_build_dialog", None)
            )
        self._build_dialog.reload()
        self._build_dialog.show()
        self._build_dialog.raise_()
        self._build_dialog.activateWindow()


class ConnectedAscendancyOverlay(AscendancyOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = ConnectedAscendancyBuildDialog(self)
            self._build_dialog.finished.connect(
                lambda _: setattr(self, "_build_dialog", None)
            )
        self._build_dialog.reload()
        self._build_dialog.show()
        self._build_dialog.raise_()
        self._build_dialog.activateWindow()


class IntegratedTreeOverlay(ConnectedAscendancyOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = IntegratedTreeBuildDialog(self)
            self._build_dialog.finished.connect(
                lambda _: setattr(self, "_build_dialog", None)
            )
        self._build_dialog.reload()
        self._build_dialog.show()
        self._build_dialog.raise_()
        self._build_dialog.activateWindow()


class NativeAscendancyOverlay(IntegratedTreeOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = NativeAscendancyBuildDialog(self)
            self._build_dialog.finished.connect(
                lambda _: setattr(self, "_build_dialog", None)
            )
        self._build_dialog.reload()
        self._build_dialog.show()
        self._build_dialog.raise_()
        self._build_dialog.activateWindow()


class RestoredAscendancyOverlay(NativeAscendancyOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = RestoredAscendancyBuildDialog(self)
            self._build_dialog.finished.connect(
                lambda _: setattr(self, "_build_dialog", None)
            )
        self._build_dialog.reload()
        self._build_dialog.show()
        self._build_dialog.raise_()
        self._build_dialog.activateWindow()


class LocalizedOverlay(RestoredAscendancyOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = LocalizedOverlayBuildDialog(self)
            self._build_dialog.finished.connect(
                lambda _: setattr(self, "_build_dialog", None)
            )
        self._build_dialog.reload()
        self._build_dialog.show()
        self._build_dialog.raise_()
        self._build_dialog.activateWindow()


class StrictNearestOverlay(LocalizedOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = StrictNearestBuildDialog(self)
            self._build_dialog.finished.connect(
                lambda _: setattr(self, "_build_dialog", None)
            )
        self._build_dialog.reload()
        self._build_dialog.show()
        self._build_dialog.raise_()
        self._build_dialog.activateWindow()


class MasteryAndQuestOverlay(StrictNearestOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = MasteryAndQuestBuildDialog(self)
            self._build_dialog.finished.connect(
                lambda _: setattr(self, "_build_dialog", None)
            )
        self._build_dialog.reload()
        self._build_dialog.show()
        self._build_dialog.raise_()
        self._build_dialog.activateWindow()


class CompactBuildOverlay(MasteryAndQuestOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = CompactBuildDialog(self)
            self._build_dialog.finished.connect(
                lambda _: setattr(self, "_build_dialog", None)
            )
        self._build_dialog.reload()
        self._build_dialog.show()
        self._build_dialog.raise_()
        self._build_dialog.activateWindow()


class AssetFramedOverlay(CompactBuildOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = AssetFramedBuildDialog(self)
            self._build_dialog.finished.connect(
                lambda _: setattr(self, "_build_dialog", None)
            )
        self._build_dialog.reload()
        self._build_dialog.show()
        self._build_dialog.raise_()
        self._build_dialog.activateWindow()


class PolishedOverlay(AssetFramedOverlay):
    def _setup_ui(self):
        super()._setup_ui()
        self._style_build_button()

    def _refresh_header(self):
        super()._refresh_header()
        self._style_build_button()

    def _style_build_button(self):
        if not hasattr(self, "build_btn"):
            return
        self.build_btn.setText("")
        self.build_btn.setIcon(build_tree_icon())
        self.build_btn.setIconSize(QSize(22, 22))
        self.build_btn.setStyleSheet("""
            QPushButton { background:transparent; border:0; padding:0; }
            QPushButton:hover { background:rgba(122,83,30,.18); border:0; }
            QPushButton:pressed { background:rgba(172,124,47,.24); }
        """)

    def _settings(self):
        overlay_was_visible = self.isVisible()
        layout_was_visible = bool(
            self._layout_dialog is not None and self._layout_dialog.isVisible()
        )
        build_was_visible = bool(
            self._build_dialog is not None and self._build_dialog.isVisible()
        )
        regex_was_visible = bool(
            getattr(self, "_regex_dialog", None) is not None
            and self._regex_dialog.isVisible()
        )
        if layout_was_visible:
            self._layout_dialog.hide()
        if build_was_visible:
            self._build_dialog.hide()
        if regex_was_visible:
            # hide() эмитит hidden -> _restore_after_regex; без сброса state оверлей всплывёт поверх настроек
            self._regex_restore_state = None
            self._regex_dialog.hide()
        dialog = Poe1SettingsDialog(self.settings, None)
        dialog.move(self.x() + (self.width() - dialog.width()) // 2, self.y() + 40)
        if overlay_was_visible:
            self.hide()
        result = dialog.exec_()
        if overlay_was_visible:
            self.show()
            self.raise_()
        if layout_was_visible and self._layout_dialog is not None:
            self._layout_dialog.show()
            self._layout_dialog.raise_()
        if build_was_visible and self._build_dialog is not None:
            self._build_dialog.show()
            self._build_dialog.raise_()
        if regex_was_visible and self._regex_dialog is not None:
            self._regex_dialog.show()
            self._regex_dialog.raise_()
        steps_changed = getattr(dialog, "steps_changed_games", set())
        if result != QDialog.Accepted:
            if self.game in steps_changed:
                self._reload_steps()
            return
        old_game = self.game
        self.settings = dialog.get_settings()
        legacy.save_json(legacy.SETTINGS_FILE, self.settings)
        self.hotkey.restart(self.settings["hotkey"])
        self._start_hotkey()
        self._update_opacity()
        self._apply_click_through_mode()
        new_scale = float(self.settings.get("ui_scale", legacy.DEFAULT_SETTINGS["ui_scale"]))
        self._apply_ui_scale(self._ui_scale, new_scale)
        self._ui_scale = new_scale
        new_game = self.settings.get("game", legacy.DEFAULT_SETTINGS["game"])
        if new_game != old_game:
            self._close_layout_dialog()
            self._save_progress()
            self._switch_game(new_game)
        elif self.game in steps_changed:
            self._reload_steps()
        self.content.set_show_splits(
            self.settings.get("show_step_splits", legacy.DEFAULT_SETTINGS["show_step_splits"]))
        if self._build_dialog is not None:
            self._build_dialog._configure_client_monitor()
        if dialog.should_reset:
            self.content.reset()
            self.timer.reset()
            self._save_progress()

    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = PolishedBuildDialog(self)
            self._build_dialog.finished.connect(
                lambda _: setattr(self, "_build_dialog", None)
            )
        self._build_dialog.reload()
        self._build_dialog.show()
        self._build_dialog.raise_()
        self._build_dialog.activateWindow()


class ExplicitRouteOverlay(PolishedOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = ExplicitRouteBuildDialog(self)
            self._build_dialog.finished.connect(
                lambda _: setattr(self, "_build_dialog", None)
            )
        self._build_dialog.reload()
        self._build_dialog.show()
        self._build_dialog.raise_()
        self._build_dialog.activateWindow()


class EditableBuildOverlay(ExplicitRouteOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = EditableBuildDialog(self)
            self._build_dialog.finished.connect(
                lambda _: setattr(self, "_build_dialog", None)
            )
        self._build_dialog.reload()
        self._build_dialog.show()
        self._build_dialog.raise_()
        self._build_dialog.activateWindow()


class ExactManualOverlay(EditableBuildOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = ExactManualBuildDialog(self)
            self._build_dialog.finished.connect(
                lambda _: setattr(self, "_build_dialog", None)
            )
        self._build_dialog.reload()
        self._build_dialog.show()
        self._build_dialog.raise_()
        self._build_dialog.activateWindow()


class StableEditorOverlay(ExactManualOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = StableEditorBuildDialog(self)
            self._build_dialog.finished.connect(
                lambda _: setattr(self, "_build_dialog", None)
            )
        self._build_dialog.reload()
        self._build_dialog.show()
        self._build_dialog.raise_()
        self._build_dialog.activateWindow()


class ClearGemEditorOverlay(StableEditorOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = ClearGemEditorBuildDialog(self)
            self._build_dialog.finished.connect(
                lambda _: setattr(self, "_build_dialog", None)
            )
        self._build_dialog.reload()
        self._build_dialog.show()
        self._build_dialog.raise_()
        self._build_dialog.activateWindow()


class ReliableClientOverlay(ClearGemEditorOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = ReliableClientBuildDialog(self)
            self._build_dialog.finished.connect(
                lambda _: setattr(self, "_build_dialog", None)
            )
        self._build_dialog.reload()
        self._build_dialog.show()
        self._build_dialog.raise_()
        self._build_dialog.activateWindow()


class FastTreeOverlay(ReliableClientOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        created = self._build_dialog is None
        if created:
            self._build_dialog = FastBuildDialog(self)
        else:
            self._build_dialog.reload()
        self._build_dialog.show()
        self._build_dialog.raise_()
        self._build_dialog.activateWindow()


class FixedInteractionOverlay(FastTreeOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = FixedInteractionBuildDialog(self)
        else:
            self._build_dialog.reload()
        self._build_dialog.sync_window_opacity()
        self._build_dialog.show()
        self._build_dialog.raise_()
        self._build_dialog.activateWindow()

    def _settings(self):
        super()._settings()
        if self._build_dialog is not None:
            self._build_dialog.sync_window_opacity()


class MiniTreeOverlay_v51(FixedInteractionOverlay):
    def __init__(self):
        super().__init__()
        self.mini_tree = MiniPassiveRoute(self.body)
        body_layout = self.body.layout()
        body_layout.insertWidget(body_layout.indexOf(self.content), self.mini_tree)
        self.mini_tree.activated.connect(self._open_build_progress)

        self._mini_signature = None
        self._mini_refresh_timer = QTimer(self)
        self._mini_refresh_timer.setInterval(1200)
        self._mini_refresh_timer.timeout.connect(self._refresh_mini_tree)
        self._mini_refresh_timer.start()

        self._mini_monitor = None
        self._configure_mini_monitor()
        self._refresh_mini_tree(force=True)
        self._apply_welcome_visibility()

    def _configure_mini_monitor(self):
        if self._mini_monitor is not None:
            self._mini_monitor._timer.stop()
            self._mini_monitor.deleteLater()
        configured = str(self.settings.get("poe1_client_path", "")).strip()
        path = Path(configured) if configured else None
        self._mini_monitor = ClientLevelMonitor(self, path)
        self._mini_monitor.level_seen.connect(self._on_mini_level_seen)
        self._mini_monitor.start()

    def _on_mini_level_seen(self, character_name, character_class, level):
        profile = self.active_profile()
        bound_name = str(profile.get("log_character_name", "")).strip()
        if bound_name and character_name.casefold() != bound_name.casefold():
            return
        build = profile.get("build") or {}
        profile_name = str(profile.get("name", "")).strip()
        same_name = profile_name.casefold() == character_name.casefold()
        compatible = class_matches(
            str(build.get("class", "")),
            str(build.get("ascendancy", "")),
            character_class,
        )
        if not bound_name and not same_name and not compatible:
            return
        profile["log_character_name"] = character_name
        new_level = clamp_level(level)
        changed = int(profile.get("level", 1)) != new_level
        profile["level"] = new_level
        self.save_profiles()
        if changed:
            self._refresh_mini_tree(force=True)
            if self._build_dialog is not None:
                self._build_dialog.refresh_level()

    def _profile_signature(self):
        profile = self.active_profile()
        build = profile.get("build") or {}
        state = build.get("manual_editor") or {}
        stages = state.get("passive_stages") or []
        route = tuple(
            (int(stage.get("level", 1)), tuple(map(str, stage.get("allocation_order", []))))
            for stage in stages
        )
        if not route:
            route = (tuple(map(str, state.get("allocation_order", []))),)
        return profile.get("id"), int(profile.get("level", 1)), route

    def _refresh_mini_tree(self, force=False):
        signature = self._profile_signature()
        if not force and signature == self._mini_signature:
            return
        self._mini_signature = signature
        profile = self.active_profile()
        self.mini_tree.set_build_level(
            profile.get("build") or {}, int(profile.get("level", 1))
        )
        self._apply_welcome_visibility()

    def _apply_welcome_visibility(self):
        super()._apply_welcome_visibility()
        if hasattr(self, "mini_tree"):
            has_route = bool(self.mini_tree._visible_nodes)
            self.mini_tree.setVisible(
                self.game == legacy.GAME_POE1 and self.content.isVisible() and has_route
            )

    def _interactive_widgets(self):
        widgets = super()._interactive_widgets()
        if hasattr(self, "mini_tree"):
            widgets.append(self.mini_tree)
        return widgets

    def create_profile(self, name):
        super().create_profile(name)
        self._refresh_mini_tree(force=True)

    def switch_profile(self, profile_id):
        super().switch_profile(profile_id)
        self._refresh_mini_tree(force=True)

    def _settings(self):
        old_path = str(self.settings.get("poe1_client_path", "")).strip()
        super()._settings()
        new_path = str(self.settings.get("poe1_client_path", "")).strip()
        if old_path != new_path:
            self._configure_mini_monitor()

    def _switch_game(self, game):
        super()._switch_game(game)
        if hasattr(self, "mini_tree"):
            self._refresh_mini_tree(force=True)

    def _open_build_progress(self):
        previous.editor_release.ManualBuildEditor = previous.ManualBuildEditor
        super()._open_build_progress()


class MiniTreeOverlay_v52(MiniTreeOverlay_v51):
    pass


class MiniTreeOverlay_v53(MiniTreeOverlay_v52):
    def showEvent(self, event):
        super().showEvent(event)
        self._refresh_mini_tree(force=True)


class MiniTreeOverlay_v54(MiniTreeOverlay_v53):
    def __init__(self):
        self._mini_hidden_by_user = False
        self._mini_panel = None
        super().__init__()

        body_layout = self.body.layout()
        body_layout.removeWidget(self.mini_tree)

        self._mini_panel = QWidget(
            self,
            Qt.Tool
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.WindowDoesNotAcceptFocus,
        )
        self._mini_panel.setAttribute(Qt.WA_TranslucentBackground, True)
        self._mini_panel.setAttribute(Qt.WA_NoSystemBackground, True)
        self._mini_panel.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self._mini_panel.setStyleSheet("background: transparent; border: 0;")
        panel_layout = QHBoxLayout(self._mini_panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(0)
        self.mini_tree.setParent(self._mini_panel)
        self.mini_tree.setFixedWidth(190)
        panel_layout.addWidget(self.mini_tree)
        self._mini_panel.setFixedSize(190, 56)
        self._mini_panel.setWindowOpacity(1.0)

        self.layout_hotkey.triggered.connect(self._toggle_mini_tree)
        self._position_mini_panel()
        self._sync_mini_panel_visibility()

    def _start_hotkey(self):
        super()._start_hotkey()
        if self.game == legacy.GAME_POE1:
            self.layout_hotkey.restart(
                self.settings.get("layout_hotkey", legacy.DEFAULT_SETTINGS["layout_hotkey"])
            )

    def _position_mini_panel(self):
        if self._mini_panel is None:
            return
        gap = 8
        x = self.frameGeometry().right() + gap
        y = self.y() + max(self.header.height(), 54)
        screen = QApplication.screenAt(self.frameGeometry().center())
        geometry = screen.availableGeometry() if screen else QApplication.primaryScreen().availableGeometry()
        if x + self._mini_panel.width() > geometry.right():
            x = self.x() - self._mini_panel.width() - gap
        y = max(geometry.top(), min(y, geometry.bottom() - self._mini_panel.height()))
        self._mini_panel.move(QPoint(x, y))

    def _sync_mini_panel_visibility(self):
        if self._mini_panel is None:
            return
        should_show = (
            self.isVisible()
            and self.game == legacy.GAME_POE1
            and bool(self.mini_tree._visible_nodes)
            and not self._mini_hidden_by_user
        )
        self._mini_panel.setVisible(should_show)
        if should_show:
            self._position_mini_panel()
            self._mini_panel.raise_()

    def _toggle_mini_tree(self):
        if self.game != legacy.GAME_POE1:
            return
        self._mini_hidden_by_user = not self._mini_hidden_by_user
        self._sync_mini_panel_visibility()

    def _refresh_mini_tree(self, force=False):
        super()._refresh_mini_tree(force)
        if self._mini_panel is not None:
            self._sync_mini_panel_visibility()

    def showEvent(self, event):
        super().showEvent(event)
        self._position_mini_panel()
        self._sync_mini_panel_visibility()

    def hideEvent(self, event):
        if self._mini_panel is not None:
            self._mini_panel.hide()
        super().hideEvent(event)

    def moveEvent(self, event):
        super().moveEvent(event)
        self._position_mini_panel()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_mini_panel()

    def _update_opacity(self):
        super()._update_opacity()
        if self._mini_panel is not None:
            self._mini_panel.setWindowOpacity(1.0)

    def closeEvent(self, event):
        if self._mini_panel is not None:
            self._mini_panel.close()
        super().closeEvent(event)


class MiniTreeOverlay_v55(MiniTreeOverlay_v54):
    def __init__(self):
        super().__init__()
        self.mini_tree.setFixedSize(88, 38)
        self._mini_panel.setFixedSize(88, 38)
        self._position_mini_panel()

    def _position_mini_panel(self):
        if self._mini_panel is None:
            return
        gap = 2
        x = self.frameGeometry().right() + gap
        y = self.y() + max(self.header.height(), 54)
        screen = QApplication.screenAt(self.frameGeometry().center())
        geometry = screen.availableGeometry() if screen else QApplication.primaryScreen().availableGeometry()
        if x + self._mini_panel.width() > geometry.right():
            x = self.x() - self._mini_panel.width() - gap
        y = max(geometry.top(), min(y, geometry.bottom() - self._mini_panel.height()))
        self._mini_panel.move(QPoint(x, y))


class MiniTreeOverlay_v56(MiniTreeOverlay_v55):
    def __init__(self):
        super().__init__()
        self._resize_mini_panel()

    def _resize_mini_panel(self):
        if self._mini_panel is None:
            return
        size = self.mini_tree.size()
        self._mini_panel.setFixedSize(size)
        self._position_mini_panel()

    def _refresh_mini_tree(self, force=False):
        super()._refresh_mini_tree(force)
        if self._mini_panel is not None:
            self._resize_mini_panel()

    def _position_mini_panel(self):
        if self._mini_panel is None:
            return
        gap = 2
        x = self.frameGeometry().right() + gap
        y = self.y() + max(self.header.height(), 54)
        screen = QApplication.screenAt(self.frameGeometry().center())
        geometry = screen.availableGeometry() if screen else QApplication.primaryScreen().availableGeometry()
        if x + self._mini_panel.width() > geometry.right():
            x = self.x() - self._mini_panel.width() - gap
        y = max(geometry.top(), min(y, geometry.bottom() - self._mini_panel.height()))
        self._mini_panel.move(QPoint(x, y))


class MiniTreeOverlay_v57(MiniTreeOverlay_v56):
    def __init__(self):
        super().__init__()
        self.mini_tree._build_tree_layout()
        self._resize_mini_panel()


class MiniTreeOverlay_v59(MiniTreeOverlay_v57):
    pass


class MiniTreeAndGemsOverlay(MiniTreeOverlay_v59):
    def __init__(self):
        self._mini_gem_panel = None
        self.mini_gems = None
        super().__init__()

        self._mini_gem_panel = QWidget(
            self,
            Qt.Tool
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.WindowDoesNotAcceptFocus,
        )
        self._mini_gem_panel.setAttribute(Qt.WA_TranslucentBackground, True)
        self._mini_gem_panel.setAttribute(Qt.WA_NoSystemBackground, True)
        self._mini_gem_panel.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self._mini_gem_panel.setStyleSheet("background: transparent; border: 0;")
        layout = QHBoxLayout(self._mini_gem_panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.mini_gems = MiniGemLinks(self._mini_gem_panel)
        layout.addWidget(self.mini_gems)
        self._refresh_mini_gems()

    def _profile_signature(self):
        base = super()._profile_signature()
        build = self.active_profile().get("build") or {}
        stages = []
        for stage in build.get("gem_sets", []):
            links = tuple(
                tuple((gem.get("name", ""), bool(gem.get("support"))) for gem in link.get("gems", []))
                for link in stage.get("links", [])
            )
            stages.append((int(stage.get("level", 1)), links))
        return base, tuple(stages)

    def _refresh_mini_gems(self):
        if self.mini_gems is None or self._mini_gem_panel is None:
            return
        profile = self.active_profile()
        self.mini_gems.set_build_level(
            profile.get("build") or {}, int(profile.get("level", 1))
        )
        self._mini_gem_panel.setFixedSize(self.mini_gems.size())
        self._mini_gem_panel.setWindowOpacity(1.0)
        self._position_mini_gem_panel()
        self._sync_mini_gem_visibility()

    def _refresh_mini_tree(self, force=False):
        super()._refresh_mini_tree(force)
        if self.mini_gems is not None:
            self._refresh_mini_gems()

    def _position_mini_panel(self):
        super()._position_mini_panel()
        self._position_mini_gem_panel()

    def _position_mini_gem_panel(self):
        if self._mini_gem_panel is None or self._mini_panel is None:
            return
        right_side = self._mini_panel.x() >= self.x()
        x = (
            self._mini_panel.x()
            if right_side
            else self._mini_panel.geometry().right() - self._mini_gem_panel.width() + 1
        )
        y = self._mini_panel.geometry().bottom() + 3
        self._mini_gem_panel.move(QPoint(x, y))

    def _sync_mini_panel_visibility(self):
        super()._sync_mini_panel_visibility()
        self._sync_mini_gem_visibility()

    def _sync_mini_gem_visibility(self):
        if self._mini_gem_panel is None or self.mini_gems is None:
            return
        show = self._mini_panel.isVisible() and bool(self.mini_gems._links)
        self._mini_gem_panel.setVisible(show)
        if show:
            self._position_mini_gem_panel()
            self._mini_gem_panel.raise_()

    def hideEvent(self, event):
        if self._mini_gem_panel is not None:
            self._mini_gem_panel.hide()
        super().hideEvent(event)

    def _update_opacity(self):
        super()._update_opacity()
        if self._mini_gem_panel is not None:
            self._mini_gem_panel.setWindowOpacity(1.0)

    def closeEvent(self, event):
        if self._mini_gem_panel is not None:
            self._mini_gem_panel.close()
        super().closeEvent(event)


class StagedGemOverlay(MiniTreeAndGemsOverlay):
    def __init__(self):
        self._mini_suspended = False
        super().__init__()
        for panel in (self._mini_panel, self._mini_gem_panel):
            was_visible = panel.isVisible()
            panel.setWindowFlag(Qt.WindowStaysOnTopHint, False)
            if was_visible:
                panel.show()

    def _sync_mini_panel_visibility(self):
        if getattr(self, "_mini_suspended", False):
            if self._mini_panel is not None:
                self._mini_panel.hide()
            if self._mini_gem_panel is not None:
                self._mini_gem_panel.hide()
            return
        super()._sync_mini_panel_visibility()

    def _open_build_progress(self):
        self._mini_suspended = True
        self._sync_mini_panel_visibility()
        try:
            super()._open_build_progress()
        except Exception:
            self._mini_suspended = False
            self._sync_mini_panel_visibility()
            raise
        if self._build_dialog is not None:
            self._build_dialog.installEventFilter(self)

    def eventFilter(self, watched, event):
        if watched is self._build_dialog and event.type() in (QEvent.Hide, QEvent.Close):
            QTimer.singleShot(0, self._restore_mini_huds)
        return super().eventFilter(watched, event)

    def _restore_mini_huds(self):
        if self._build_dialog is not None and self._build_dialog.isVisible():
            return
        self._mini_suspended = False
        self._sync_mini_panel_visibility()


class GemOverviewOverlay(StagedGemOverlay):
    pass


class FixedGemOverviewOverlay(GemOverviewOverlay):
    def _open_build_progress(self):
        editor_bridge.ManualBuildEditor = ManualBuildEditor
        editor_bridge.editor_release.ManualBuildEditor = ManualBuildEditor
        editor_release.ManualBuildEditor = ManualBuildEditor
        super()._open_build_progress()


class PobMiniPreviewOverlay(FixedGemOverviewOverlay):
    def _profile_signature(self):
        base = super()._profile_signature()
        build = self.active_profile().get("build") or {}
        trees = tuple(
            (
                int(stage.get("level", 1)),
                tuple(str(node) for node in stage.get("nodes", [])),
            )
            for stage in build.get("trees", [])
        )
        return base, build.get("format", ""), trees

    def _sync_mini_gem_visibility(self):
        if self._mini_gem_panel is None or self.mini_gems is None:
            return
        show = (
            self.isVisible()
            and self.game == legacy.GAME_POE1
            and bool(self.mini_gems._links)
            and not self._mini_hidden_by_user
            and not getattr(self, "_mini_suspended", False)
        )
        self._mini_gem_panel.setVisible(show)
        if show:
            self._position_mini_gem_panel()
            self._mini_gem_panel.raise_()


class DetailedMiniGemOverlay(PobMiniPreviewOverlay):
    pass


class CompleteMiniTreeOverlay(DetailedMiniGemOverlay):
    pass


class KindCorrectGemOverlay(CompleteMiniTreeOverlay):
    pass


class CompactHeaderOverlay(KindCorrectGemOverlay):
    def __init__(self, *args, **kwargs):
        _install_compact_metrics()
        super().__init__(*args, **kwargs)

    def _refresh_header(self):
        super()._refresh_header()
        self.header.layout().setSpacing(max(6, int(round(8 * legacy.Style.ui_scale()))))
        if hasattr(self, "build_btn"):
            icon_size = max(14, int(round(18 * legacy.Style.ui_scale())))
            self.build_btn.setIcon(build_tree_icon(icon_size))
            self.build_btn.setIconSize(QSize(icon_size, icon_size))


class CompactHeaderIconOverlay(CompactHeaderOverlay):
    def _style_build_button(self):
        super()._style_build_button()
        if hasattr(self, "build_btn"):
            size = max(14, int(round(18 * legacy.Style.ui_scale())))
            self.build_btn.setIcon(build_tree_icon(size))
            self.build_btn.setIconSize(QSize(size, size))


from actpilot.build_dialog import (
    AscendancyBuildDialog,
    AssetFramedBuildDialog,
    BookOnlyBuildDialog,
    BuildProgressDialog,
    CleanArtworkBuildDialog,
    CleanBuildDialog,
    ClearGemEditorBuildDialog,
    CombinedBuildDialog,
    CompactBuildDialog,
    ConnectedAscendancyBuildDialog,
    ContinuousPassiveBuildDialog,
    CorrectedBuildDialog,
    CorrectedSemanticBuildDialog,
    EditableBuildDialog,
    EnhancedBuildProgressDialog,
    ExactManualBuildDialog,
    ExplicitRouteBuildDialog,
    FastBuildDialog,
    FinalBuildDialog,
    FinalLevelMappedBuildDialog,
    FixedInteractionBuildDialog,
    FixedProgressionBuildDialog,
    FullStageBuildDialog,
    ImmediateFocusBuildDialog,
    IntegratedTreeBuildDialog,
    LevelMappedBuildDialog,
    LocalizedOverlayBuildDialog,
    MasteryAndQuestBuildDialog,
    MasteryBuildDialog,
    NativeAscendancyBuildDialog,
    OrbitalBuildDialog,
    PerLevelBuildDialog,
    PolishedBuildDialog,
    ProgressionBuildDialog,
    QuestAwareBuildDialog,
    ReleaseBuildDialog,
    ReliableClientBuildDialog,
    RestoredAscendancyBuildDialog,
    RouteBuildDialog,
    ScaledGemBuildDialog,
    SemanticPassiveBuildDialog,
    SocketedGemBuildDialog,
    StableEditorBuildDialog,
    StrictNearestBuildDialog,
    StrictProgressionBuildDialog,
    TargetBuildProgressDialog,
)
class _EditorPatchTarget:
    # Инертная цель рантайм-патчей ManualBuildEditor: башня release_poe1_v41/v50, читавшая их, удалена
    ManualBuildEditor = ManualBuildEditor


editor_release = _EditorPatchTarget()
editor_bridge = _EditorPatchTarget()
editor_bridge.editor_release = editor_release
previous = editor_bridge

legacy.Overlay = Overlay
