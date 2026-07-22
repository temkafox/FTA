"""Совместимость: модуль переехал в actpilot.clientmonitor."""

from actpilot.clientmonitor import (
    TAIL_BYTES,
    find_client_log,
    ClientLevelMonitorV2 as ClientLevelMonitor,
)
