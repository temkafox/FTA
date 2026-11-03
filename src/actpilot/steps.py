"""Шаги гайда: дефолтные шаги, файлы прогресса, раскладки PoE2, разметка."""

import hashlib
import uuid
from pathlib import Path

from actpilot.data_cache import game_data
from actpilot.paths import APP_DIR, DATA_DIR, get_resource_dir
from actpilot.persistence import load_json, save_json
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


def normalize_steps(raw: dict) -> tuple[dict, bool]:
    """Приводит шаги к виду {act: [{"id","text"}]}, назначая id где его нет.

    Шаг в файле — либо строка (легаси/bundled/ручная правка), либо объект
    {"id","text"}. Возвращает (нормализованные данные, были_ли_добавлены_id).
    Идемпотентна: существующие id не трогает."""
    added = False
    result = {}
    for act, steps in (raw or {}).items():
        normalized = []
        for step in steps or []:
            if isinstance(step, dict):
                text = str(step.get("text", ""))
                step_id = step.get("id")
                if not step_id:
                    step_id = uuid.uuid4().hex
                    added = True
            else:
                text = str(step)
                step_id = uuid.uuid4().hex
                added = True
            normalized.append({"id": step_id, "text": text})
        result[act] = normalized
    return result, added


def persist_steps_with_ids(game: str, resolved_path: Path, data: dict):
    """Фиксирует стабильные id на диске, чтобы контент и редактор их разделяли.

    Пишет обратно в resolved_path; если это read-only бандл или запись упала —
    в пользовательский файл. Best-effort."""
    target = resolved_path
    if resolved_path == get_bundled_steps_file(game):
        target = get_user_steps_file(game)
    try:
        save_json(target, data)
    except OSError:
        if target != get_user_steps_file(game):
            try:
                save_json(get_user_steps_file(game), data)
            except OSError:
                pass


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


def campaign_extras(game: str) -> dict:
    """Необязательное по актам: рецепты верстака, тайники, прочее; есть только для PoE1."""
    if game != GAME_POE1:
        return {}
    return game_data("campaign_extras.json", {}).get("acts", {})


# Пользовательский steps_*.json — копия бандла с первого запуска: при смене бандла сюда добавляются отпечатки прежних актов
PREVIOUS_DEFAULT_ACTS = {
    GAME_POE1: {
        "Act 1": {"59f242e9e2b5f07b"},
        "Act 2": {"116bb4388ddd6fbc"},
        "Act 3": {"9118a369dc8d07c0"},
        "Act 4": {"d06c97236f59100a"},
        "Act 5": {"7b67a8f51ac13404"},
        "Act 6": {"866cca48cba3963f"},
        "Act 7": {"60fc1439b5e8e5cd"},
        "Act 8": {"393d9ff6bdd860f0"},
        "Act 9": {"5e15a9467797be40"},
        "Act 10": {"1b7b6d37485cf902"},
    },
}


def act_fingerprint(texts: list) -> str:
    return hashlib.sha256("\n".join(texts).encode("utf-8")).hexdigest()[:16]


def upgrade_default_steps(game: str, data: dict, defaults=None, previous=None) -> bool:
    """Заменяет акты, которые пользователь не правил, новой встроенной версией."""
    if defaults is None:
        defaults = DEFAULT_STEPS_POE2 if game == GAME_POE2 else DEFAULT_STEPS
    previous = PREVIOUS_DEFAULT_ACTS.get(game, {}) if previous is None else previous
    changed = False
    for act, fresh in defaults.items():
        steps = data.get(act)
        if not steps:
            continue
        texts = [step["text"] for step in steps]
        fresh_texts = [item if isinstance(item, str) else str(item.get("text", "")) for item in fresh]
        if texts == fresh_texts or act_fingerprint(texts) not in previous.get(act, ()):
            continue
        # Прогресс — отмеченный префикс шагов: id по позиции оставляют игрока на том же месте акта
        data[act] = [
            {"id": steps[index]["id"] if index < len(steps) else uuid.uuid4().hex, "text": text}
            for index, text in enumerate(fresh_texts)
        ]
        changed = True
    return changed


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
