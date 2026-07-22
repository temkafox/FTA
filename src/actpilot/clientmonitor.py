"""Живая линия монитора Client.txt: база ClientLevelMonitor (v2) и helper find_client_log."""

from __future__ import annotations

import os
from pathlib import Path

from PyQt5.QtCore import QObject, QTimer, pyqtSignal

from actpilot.clientlog import (
    LevelEvent,
    current_session_tail,
    parse_level_events,
    split_complete_lines,
)


TAIL_BYTES = 2_000_000


def find_client_log() -> Path | None:
    candidates = []
    for env_name in ("PROGRAMFILES(X86)", "PROGRAMFILES"):
        root = os.environ.get(env_name)
        if not root:
            continue
        for install in (
            Path(root) / "Grinding Gear Games" / "Path of Exile",
            Path(root) / "Steam" / "steamapps" / "common" / "Path of Exile",
        ):
            candidates.extend((install / "logs" / "LatestClient.txt", install / "logs" / "Client.txt"))
    documents = Path.home() / "Documents" / "My Games" / "Path of Exile" / "logs"
    candidates.extend((documents / "LatestClient.txt", documents / "Client.txt"))
    existing = [path for path in candidates if path.is_file()]
    return max(existing, key=lambda path: path.stat().st_mtime) if existing else None


class ClientLevelMonitor(QObject):
    level_seen = pyqtSignal(str, str, int)
    status_changed = pyqtSignal(str)

    def __init__(self, parent=None, path: Path | None = None):
        super().__init__(parent)
        self.path = Path(path) if path else find_client_log()
        self._position = 0
        self._identity = None
        self._pending = ""
        self._last_event = None
        self._timer = QTimer(self)
        self._timer.setInterval(750)
        self._timer.timeout.connect(self.poll)

    @staticmethod
    def _file_identity(stat):
        return stat.st_dev, stat.st_ino

    def _emit(self, event: LevelEvent):
        key = (event.name.casefold(), event.character_class.casefold(), event.level)
        if key == self._last_event:
            return
        self._last_event = key
        self.level_seen.emit(event.name, event.character_class, event.level)

    def _prime(self):
        stat = self.path.stat()
        start = max(0, stat.st_size - TAIL_BYTES)
        with self.path.open("rb") as stream:
            stream.seek(start)
            raw = stream.read()
            self._position = stream.tell()
        self._identity = self._file_identity(stat)
        self._pending = ""
        text = raw.decode("utf-8-sig", errors="replace")
        events = parse_level_events(current_session_tail(text))
        if events:
            self._emit(events[-1])

    def start(self):
        try:
            if not self.path or not self.path.is_file():
                self.status_changed.emit("Client.txt не найден — ожидаю файл; уровень можно менять вручную")
            else:
                self._prime()
                self.status_changed.emit(f"Слежу за уровнем: {self.path}")
        except OSError as error:
            self.status_changed.emit(f"Не удалось прочитать Client.txt: {error}")
        self._timer.start()

    def poll(self):
        if not self.path:
            discovered = find_client_log()
            if not discovered:
                return
            self.path = discovered
        try:
            stat = self.path.stat()
            identity = self._file_identity(stat)
            if self._identity is None or identity != self._identity or stat.st_size < self._position:
                self._prime()
                self.status_changed.emit(f"Слежу за уровнем: {self.path}")
                return
            if stat.st_size == self._position:
                return
            with self.path.open("rb") as stream:
                stream.seek(self._position)
                raw = stream.read()
                self._position = stream.tell()
            complete, self._pending = split_complete_lines(
                self._pending, raw.decode("utf-8-sig", errors="replace")
            )
            for event in parse_level_events(complete):
                self._emit(event)
        except FileNotFoundError:
            self._identity = None
            self._position = 0
            self._pending = ""
        except OSError as error:
            self.status_changed.emit(f"Ошибка чтения Client.txt: {error}")


ClientLevelMonitorV2 = ClientLevelMonitor


class ClientLevelMonitor(ClientLevelMonitorV2):
    def __init__(self, parent=None, path=None):
        self.event_is_initial = False
        super().__init__(parent, path)

    def _prime(self):
        stat = self.path.stat()
        start = max(0, stat.st_size - TAIL_BYTES)
        with self.path.open("rb") as stream:
            stream.seek(start)
            raw = stream.read()
            self._position = stream.tell()
        self._identity = self._file_identity(stat)
        self._pending = ""
        events = parse_level_events(
            current_session_tail(raw.decode("utf-8-sig", errors="replace"))
        )
        if events:
            self.event_is_initial = True
            try:
                self._emit(events[-1])
            finally:
                self.event_is_initial = False


ClientLevelMonitorV3 = ClientLevelMonitor
