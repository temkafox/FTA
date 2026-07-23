"""Совместимый фасад бывшего legacy `main`: реэкспорт живой поверхности actpilot
плюс стартовые миграции. Живые модули импортируют его как `legacy`."""

import sys
import json
from pathlib import Path

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

from actpilot.widgets import (
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
    if "show_step_splits" not in settings:
        settings["show_step_splits"] = True
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
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"Не удалось перенести старый прогресс: {exc}", file=sys.stderr)
