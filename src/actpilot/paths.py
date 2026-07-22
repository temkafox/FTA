"""Пути приложения: каталог данных, миграция portable-данных в %APPDATA%."""

import os
import shutil
import sys
from pathlib import Path

APP_NAME = "ActPilot"


def get_app_dir() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


def get_resource_dir() -> Path:
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS)
    return get_app_dir()


APP_DIR = get_app_dir()


def get_data_dir() -> Path:
    if getattr(sys, 'frozen', False):
        base = os.environ.get("APPDATA")
        root = Path(base) if base else Path.home() / "AppData" / "Roaming"
        return root / APP_NAME
    return APP_DIR / "data"


DATA_DIR = get_data_dir()
SETTINGS_FILE = DATA_DIR / "settings.json"
LEGACY_PROGRESS_FILE = DATA_DIR / "progress.json"


def _migrate_exe_adjacent_data():
    # Обязана выполниться на импорте (main тянет paths первым): Poe1Overlay читает PROFILE_FILE до ensure_dirs()
    if not getattr(sys, 'frozen', False):
        return
    old_dir = APP_DIR / "data"
    try:
        if not old_dir.is_dir():
            return
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        for source in old_dir.glob("*.json"):
            target = DATA_DIR / source.name
            if not target.exists():
                shutil.copy2(source, target)
    except OSError as exc:
        print(f"ActPilot: миграция данных пропущена: {exc}", file=sys.stderr)


_migrate_exe_adjacent_data()
