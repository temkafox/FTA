"""Атомарное чтение/запись пользовательских JSON."""

import json
import sys
from pathlib import Path


def load_json(path: Path, default: dict) -> dict:
    try:
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except OSError as exc:
        print(f"ActPilot: не удалось прочитать {path.name}: {exc}", file=sys.stderr)
    except ValueError as exc:
        print(f"ActPilot: повреждён {path.name}: {exc}", file=sys.stderr)
        try:
            path.replace(path.with_suffix(path.suffix + ".corrupt"))
        except OSError:
            pass
    return default.copy()


def save_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with open(temp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    temp.replace(path)
