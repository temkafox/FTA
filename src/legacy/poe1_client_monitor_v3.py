"""Client monitor that distinguishes startup history from live level events."""

from __future__ import annotations

from poe1_client_log_v2 import current_session_tail, parse_level_events
from poe1_client_monitor_v2 import (
    TAIL_BYTES,
    ClientLevelMonitor as BaseClientLevelMonitor,
    find_client_log,
)


class ClientLevelMonitor(BaseClientLevelMonitor):
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
