"""Шаги гайда: дефолтные шаги, файлы прогресса, раскладки PoE2, разметка."""

from pathlib import Path

from actpilot.paths import APP_DIR, DATA_DIR, get_resource_dir
from actpilot.persistence import load_json
from actpilot.style import POE_COLORS, Style


GAME_POE1 = "poe1"
GAME_POE2 = "poe2"


def get_user_steps_file(game: str) -> Path:
    return DATA_DIR / f"steps_{game}.json"


def get_bundled_steps_file(game: str) -> Path:
    name = "steps_poe2.json" if game == GAME_POE2 else "steps.json"
    return get_resource_dir() / name


def get_steps_file(game: str) -> Path:
    name = "steps_poe2.json" if game == GAME_POE2 else "steps.json"
    user = get_user_steps_file(game)
    if user.exists():
        return user
    external = APP_DIR / name
    if external.exists():
        return external
    bundled = get_resource_dir() / name
    if bundled.exists():
        return bundled
    return external


def get_progress_file(game: str) -> Path:
    if game == GAME_POE2:
        return DATA_DIR / "progress_poe2.json"
    return DATA_DIR / "progress_poe1.json"


def get_data_file(name: str) -> Path:
    external = DATA_DIR / name
    if external.exists():
        return external
    bundled = get_resource_dir() / "data" / name
    if bundled.exists():
        return bundled
    return external


POE2_LAYOUTS_FILE = "poe2_layouts.json"
POE2_LAYOUT_STEPS_FILE = "poe2_layout_steps.json"
MANOR_FLOOR_IDS = ("ogham_manor_1", "ogham_manor_2", "ogham_manor_3")


def layout_asset_path(rel_path: str) -> Path:
    rel = rel_path.replace("\\", "/")
    for base in (APP_DIR, get_resource_dir()):
        p = base / rel
        if p.is_file():
            return p
    return APP_DIR / rel


def load_poe2_layout_catalog() -> dict:
    data = load_json(get_data_file(POE2_LAYOUTS_FILE), {})
    return data.get("layouts", {})


_layout_steps_cache = None


def load_poe2_layout_steps_all() -> dict:
    global _layout_steps_cache
    if _layout_steps_cache is None:
        _layout_steps_cache = load_json(get_data_file(POE2_LAYOUT_STEPS_FILE), {})
    return _layout_steps_cache


DEFAULT_STEPS = load_json(get_bundled_steps_file(GAME_POE1), {})


DEFAULT_STEPS_POE2 = load_json(get_bundled_steps_file(GAME_POE2), {})


def format_time(seconds: float) -> str:
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"


def parse_time(value: str) -> int:
    try:
        mins, secs = value.split(":")
        return int(mins) * 60 + int(secs)
    except (ValueError, AttributeError):
        return 0


def parse_step_markup(text: str, base_color: str, done: bool = False) -> str:
    import html
    import re

    effective_base = Style.TEXT_DISABLED if done else base_color
    strike = "text-decoration:line-through;" if done else ""
    parts = []
    last = 0

    for match in re.finditer(r"\{(\w+)\|([^}]+)\}", text):
        if match.start() > last:
            plain = html.escape(text[last:match.start()])
            parts.append(
                f'<span style="color:{effective_base};{strike}">{plain}</span>'
            )

        kind = match.group(1).lower()
        inner = html.escape(match.group(2))
        color = effective_base if done else POE_COLORS.get(kind, effective_base)
        parts.append(f'<span style="color:{color};{strike}">{inner}</span>')
        last = match.end()

    if last < len(text):
        plain = html.escape(text[last:])
        parts.append(f'<span style="color:{effective_base};{strike}">{plain}</span>')

    if not parts:
        escaped = html.escape(text)
        return f'<span style="color:{effective_base};{strike}">{escaped}</span>'

    return "".join(parts)
