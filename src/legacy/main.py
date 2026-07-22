import sys
import json
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QFrame, QSlider, QDialog, QLineEdit,
    QSizePolicy, QSystemTrayIcon, QMenu, QAction, QCheckBox, QButtonGroup,
    QMessageBox,
)
from PyQt5.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve, pyqtSignal, pyqtProperty, QObject,
    QTimer, QRect, QRectF, QSize, QPoint, QPointF,
)
from PyQt5.QtGui import (
    QColor, QFont, QFontDatabase, QFontMetrics, QPainter, QPen, QBrush,
    QIcon, QPixmap, QImage, QPainterPath, QTransform, QCursor, QLinearGradient,
)
import time

from actpilot.hotkeys import HotkeyListener, display_hotkey, normalize_hotkey
from actpilot.paths import (
    APP_DIR, APP_NAME, DATA_DIR, LEGACY_PROGRESS_FILE, SETTINGS_FILE,
    get_app_dir, get_data_dir, get_resource_dir,
)
from actpilot.persistence import load_json, save_json
from actpilot.style import POE_COLORS, Style, _STYLE_NUMERIC_BASE
from actpilot.winapi import set_window_click_through
from actpilot.regex_dialog import DEFAULT_REGEXES, RegexDialog
from actpilot.steps import (
    DEFAULT_STEPS, DEFAULT_STEPS_POE2, GAME_POE1, GAME_POE2, MANOR_FLOOR_IDS,
    POE2_LAYOUTS_FILE, POE2_LAYOUT_STEPS_FILE, _layout_steps_cache, format_time,
    get_data_file, get_progress_file, get_steps_file, layout_asset_path,
    load_poe2_layout_catalog, load_poe2_layout_steps_all, parse_step_markup,
)


# ==================== СТИЛИ ====================
# Style/_STYLE_NUMERIC_BASE/POE_COLORS живут в actpilot.style


# ==================== ПУТИ ====================
# APP_DIR/DATA_DIR/SETTINGS_FILE и миграция в %APPDATA% живут в actpilot.paths

# Игры/дефолтные шаги/файлы прогресса/разметка живут в actpilot.steps


# UI-виджеты и художественные хелперы вынесены в actpilot.widgets;
# реэкспорт держит совместимость с legacy.<имя> из башни.
from actpilot.widgets import (  # noqa: E402
    Checkbox, ContentArea, CornerResizeHandles, DEFAULT_SETTINGS, FantasyProgressBar,
    GroupWidget, HotkeyFooter, LayoutHintDialog, StepItem, Timer, TimerLabel,
    WelcomePanel, draw_nine_slice, ensure_cormorant_loaded, is_manor_floor_step,
    load_background_pixmap, load_poe2_layout_steps, load_ui_pixmap, make_icon_button,
    register_ui_font, resolve_layout_id, scaled_ui_pixmap, set_widget_transparent,
    timer_display_font, timer_row_height,
)


def migrate_settings(settings: dict) -> bool:
    """Дополняет настройки новыми ключами, не трогая пользовательские значения."""
    changed = False
    if int(settings.get("regex_defaults_version", 0)) < 2:
        settings.setdefault("regexes", [entry.copy() for entry in DEFAULT_REGEXES])
        settings["regex_defaults_version"] = 2
        changed = True
    if int(settings.get("hotkey_defaults_version", 0)) < 2:
        settings.setdefault("previous_hotkey", normalize_hotkey("Ctrl+F3"))
        settings.setdefault("regex_hotkey", normalize_hotkey("F6"))
        settings["hotkey_defaults_version"] = 2
        changed = True
    return changed


def ensure_dirs():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def migrate_legacy_progress():
    if LEGACY_PROGRESS_FILE.exists() and not get_progress_file(GAME_POE1).exists():
        try:
            with open(LEGACY_PROGRESS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            save_json(get_progress_file(GAME_POE1), data)
        except Exception:
            pass


class SettingsDialog(QDialog):
    DIALOG_W = 340
    DIALOG_H = 520

    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self.settings = settings.copy()
        self._should_reset = False

        screen = QApplication.primaryScreen()
        max_h = int(screen.availableGeometry().height() * 0.85) if screen else 700
        dialog_h = min(self.DIALOG_H, max_h)

        self.setFixedSize(self.DIALOG_W, dialog_h)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)

        self.setStyleSheet(f"""
            QDialog {{
                background: {Style.BG};
                border-radius: {Style.RAD_L}px;
                border: 1px solid {Style.BORDER};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(Style.PAD_M)
        layout.setContentsMargins(Style.PAD_XL, Style.PAD_XL, Style.PAD_XL, Style.PAD_XL)

        title = QLabel("Settings")
        title.setFont(QFont("Segoe UI", 18, QFont.Light))
        title.setStyleSheet(f"color: {Style.TEXT_PRIMARY};")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 6px;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(255, 255, 255, 0.15);
                border-radius: 3px;
                min-height: 40px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: rgba(255, 255, 255, 0.25);
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{ height: 0; }}
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {{ background: none; }}
        """)

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        content = QVBoxLayout(scroll_content)
        content.setSpacing(Style.PAD_M)
        content.setContentsMargins(0, 0, 4, 0)

        # Game
        self.poe2_checkbox = QCheckBox("Path of Exile 2")
        self.poe2_checkbox.setFont(QFont("Segoe UI", 11))
        self.poe2_checkbox.setChecked(settings.get("game", GAME_POE2) == GAME_POE2)
        self.poe2_checkbox.setCursor(Qt.PointingHandCursor)
        self.poe2_checkbox.setStyleSheet(f"""
            QCheckBox {{
                color: {Style.TEXT_SECONDARY};
                spacing: {Style.PAD_S}px;
            }}
            QCheckBox:hover {{
                color: {Style.TEXT_PRIMARY};
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1.5px solid rgba(255, 255, 255, 0.25);
                background: {Style.BG_SECONDARY};
            }}
            QCheckBox::indicator:hover {{
                border-color: rgba(255, 255, 255, 0.4);
            }}
            QCheckBox::indicator:checked {{
                background: {Style.ACCENT};
                border-color: {Style.ACCENT};
            }}
        """)
        content.addWidget(self.poe2_checkbox)

        self.click_through_checkbox = QCheckBox("Клики сквозь оверлей")
        self.click_through_checkbox.setFont(QFont("Segoe UI", 11))
        self.click_through_checkbox.setChecked(settings.get("click_through", False))
        self.click_through_checkbox.setCursor(Qt.PointingHandCursor)
        self.click_through_checkbox.setStyleSheet(self.poe2_checkbox.styleSheet())
        content.addWidget(self.click_through_checkbox)

        content.addSpacing(Style.PAD_XS)

        hk_label = QLabel("Hotkey")
        hk_label.setFont(QFont("Segoe UI", 10))
        hk_label.setStyleSheet(f"color: {Style.TEXT_MUTED};")
        content.addWidget(hk_label)
        
        self.hotkey_input = QLineEdit(display_hotkey(settings.get("hotkey", DEFAULT_SETTINGS["hotkey"])))
        self.hotkey_input.setFont(QFont("Segoe UI", 12))
        self.hotkey_input.setFixedHeight(44)
        self.hotkey_input.setStyleSheet(f"""
            QLineEdit {{
                background: {Style.BG_SECONDARY};
                border: 1px solid {Style.BORDER};
                border-radius: {Style.RAD_S}px;
                padding: 0 {Style.PAD_M}px;
                color: {Style.TEXT_PRIMARY};
            }}
            QLineEdit:focus {{
                border-color: {Style.ACCENT};
            }}
        """)
        content.addWidget(self.hotkey_input)

        op_label = QLabel("Opacity")
        op_label.setFont(QFont("Segoe UI", 10))
        op_label.setStyleSheet(f"color: {Style.TEXT_MUTED};")
        content.addWidget(op_label)
        
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setFixedHeight(28)
        self.opacity_slider.setRange(50, 100)
        self.opacity_slider.setValue(int(settings.get("opacity", 0.95) * 100))
        self.opacity_slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                background: {Style.BG_SECONDARY};
                height: 4px;
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: {Style.TEXT_SECONDARY};
                width: 16px;
                height: 16px;
                margin: -6px 0;
                border-radius: 8px;
            }}
            QSlider::handle:horizontal:hover {{
                background: {Style.TEXT_PRIMARY};
            }}
            QSlider::sub-page:horizontal {{
                background: {Style.ACCENT};
                border-radius: 2px;
            }}
        """)
        content.addWidget(self.opacity_slider)

        layout_hk_label = QLabel("Хоткей лейаута (PoE2)")
        layout_hk_label.setFont(QFont("Segoe UI", 10))
        layout_hk_label.setStyleSheet(f"color: {Style.TEXT_MUTED};")
        content.addWidget(layout_hk_label)

        self.layout_hotkey_input = QLineEdit(
            display_hotkey(settings.get("layout_hotkey", DEFAULT_SETTINGS["layout_hotkey"]))
        )
        self.layout_hotkey_input.setFont(QFont("Segoe UI", 12))
        self.layout_hotkey_input.setFixedHeight(44)
        self.layout_hotkey_input.setStyleSheet(self.hotkey_input.styleSheet())
        content.addWidget(self.layout_hotkey_input)

        layout_op_label = QLabel("Прозрачность подсказки")
        layout_op_label.setFont(QFont("Segoe UI", 10))
        layout_op_label.setStyleSheet(f"color: {Style.TEXT_MUTED};")
        content.addWidget(layout_op_label)

        self.layout_opacity_slider = QSlider(Qt.Horizontal)
        self.layout_opacity_slider.setFixedHeight(28)
        self.layout_opacity_slider.setRange(50, 100)
        self.layout_opacity_slider.setValue(
            int(settings.get("layout_opacity", DEFAULT_SETTINGS["layout_opacity"]) * 100)
        )
        self.layout_opacity_slider.setStyleSheet(self.opacity_slider.styleSheet())
        content.addWidget(self.layout_opacity_slider)

        scale_label = QLabel("Масштаб интерфейса")
        scale_label.setFont(QFont("Segoe UI", 10))
        scale_label.setStyleSheet(f"color: {Style.TEXT_MUTED};")
        content.addWidget(scale_label)

        self.scale_slider = QSlider(Qt.Horizontal)
        self.scale_slider.setFixedHeight(28)
        self.scale_slider.setRange(int(Style.UI_SCALE_MIN * 100), int(Style.UI_SCALE_MAX * 100))
        self.scale_slider.setValue(int(settings.get("ui_scale", 1.0) * 100))
        self.scale_slider.setStyleSheet(self.opacity_slider.styleSheet())
        content.addWidget(self.scale_slider)

        self.scale_value_label = QLabel(f"{self.scale_slider.value()}%")
        self.scale_value_label.setFont(QFont("Segoe UI", 10))
        self.scale_value_label.setStyleSheet(f"color: {Style.TEXT_SECONDARY};")
        self.scale_value_label.setAlignment(Qt.AlignRight)
        self.scale_slider.valueChanged.connect(
            lambda v: self.scale_value_label.setText(f"{v}%")
        )
        content.addWidget(self.scale_value_label)

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll, 1)

        reset_btn = QPushButton("Reset progress")
        reset_btn.setFont(QFont("Segoe UI", 11))
        reset_btn.setFixedHeight(40)
        reset_btn.setCursor(Qt.PointingHandCursor)
        reset_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {Style.DANGER};
            }}
            QPushButton:hover {{
                color: #fca5a5;
            }}
        """)
        reset_btn.clicked.connect(self._reset)
        layout.addWidget(reset_btn)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(Style.PAD_M)
        
        cancel = QPushButton("Cancel")
        cancel.setFont(QFont("Segoe UI", 11))
        cancel.setFixedHeight(44)
        cancel.setCursor(Qt.PointingHandCursor)
        cancel.setStyleSheet(f"""
            QPushButton {{
                background: {Style.BG_SECONDARY};
                border: 1px solid {Style.BORDER};
                border-radius: {Style.RAD_S}px;
                color: {Style.TEXT_SECONDARY};
            }}
            QPushButton:hover {{
                background: {Style.HOVER};
            }}
        """)
        cancel.clicked.connect(self.reject)
        btn_layout.addWidget(cancel)
        
        save = QPushButton("Save")
        save.setFont(QFont("Segoe UI", 11, QFont.DemiBold))
        save.setFixedHeight(44)
        save.setCursor(Qt.PointingHandCursor)
        save.setStyleSheet(f"""
            QPushButton {{
                background: {Style.ACCENT};
                border: none;
                border-radius: {Style.RAD_S}px;
                color: {Style.BG};
            }}
            QPushButton:hover {{
                background: #22c55e;
            }}
        """)
        save.clicked.connect(self.accept)
        btn_layout.addWidget(save)
        
        layout.addLayout(btn_layout)
    
    def _reset(self):
        self._should_reset = True
        self.accept()
    
    def get_settings(self):
        self.settings["hotkey"] = normalize_hotkey(self.hotkey_input.text())
        self.settings["opacity"] = self.opacity_slider.value() / 100
        self.settings["layout_hotkey"] = normalize_hotkey(self.layout_hotkey_input.text())
        self.settings["layout_opacity"] = self.layout_opacity_slider.value() / 100
        self.settings["game"] = GAME_POE2 if self.poe2_checkbox.isChecked() else GAME_POE1
        self.settings["click_through"] = self.click_through_checkbox.isChecked()
        self.settings["ui_scale"] = self.scale_slider.value() / 100.0
        return self.settings
    
    @property
    def should_reset(self):
        return self._should_reset


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    ensure_cormorant_loaded()
    app.setFont(QFont("Segoe UI", 10))
    
    window = Overlay()
    window.show()
    
    sys.exit(app.exec_())
