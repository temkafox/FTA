import os
import sys
from pathlib import Path

# Бэкенды выбираются при импорте pynput/Qt — env до добавления путей и импортов
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("PYNPUT_BACKEND_KEYBOARD", "dummy")
os.environ.setdefault("PYNPUT_BACKEND_MOUSE", "dummy")

ROOT = Path(__file__).resolve().parent.parent
for entry in (str(ROOT), str(ROOT / "src" / "legacy")):
    if entry not in sys.path:
        sys.path.insert(0, entry)
