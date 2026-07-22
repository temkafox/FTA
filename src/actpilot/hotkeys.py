"""Глобальные хоткеи: нормализация, отображение, pynput-слушатель."""

from PyQt5.QtCore import QObject, pyqtSignal
from pynput import keyboard


def normalize_hotkey(hotkey: str) -> str:
    """Приводит хотkey к формату pynput GlobalHotKeys, напр. F4 -> <f4>."""
    s = hotkey.strip().lower().replace(" ", "")
    if not s:
        return "<f4>"

    parts = []
    for part in s.split("+"):
        if part.startswith("<") and part.endswith(">"):
            parts.append(part)
        elif part in ("ctrl", "control", "alt", "shift", "cmd", "win"):
            parts.append("<ctrl>" if part == "control" else f"<{part}>")
        elif len(part) >= 2 and part[0] == "f" and part[1:].isdigit():
            parts.append(f"<{part}>")
        elif len(part) == 1:
            parts.append(part)
        else:
            parts.append(part)
    return "+".join(parts)


def display_hotkey(hotkey: str) -> str:
    normalized = normalize_hotkey(hotkey)
    labels = {"ctrl": "Ctrl", "alt": "Alt", "shift": "Shift", "cmd": "Win", "win": "Win"}
    parts = []
    for part in normalized.split("+"):
        inner = part[1:-1] if part.startswith("<") and part.endswith(">") else part
        if inner.startswith("f") and inner[1:].isdigit():
            parts.append(inner.upper())
        else:
            parts.append(labels.get(inner, inner.upper() if len(inner) == 1 else inner))
    return "+".join(parts)


class HotkeyListener(QObject):
    triggered = pyqtSignal()
    failed = pyqtSignal(str)

    def __init__(self, hotkey: str):
        super().__init__()
        self._hotkey = normalize_hotkey(hotkey)
        self._listener = None

    def start(self):
        self.stop()
        try:
            self._listener = keyboard.GlobalHotKeys({self._hotkey: self._emit})
            self._listener.start()
        except Exception as e:
            print(f"Hotkey error: {e}")
            self.failed.emit(str(e))

    def stop(self):
        if self._listener:
            try:
                self._listener.stop()
                if hasattr(self._listener, "join"):
                    self._listener.join(0.5)
            except Exception:
                pass
            self._listener = None

    def _emit(self):
        self.triggered.emit()

    def restart(self, hotkey: str):
        self._hotkey = normalize_hotkey(hotkey)
        self.start()
