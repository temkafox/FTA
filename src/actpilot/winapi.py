"""Win32-интеграция оверлея."""

import sys


def set_window_click_through(widget, enabled: bool):
    """Windows: пропускать клики сквозь окно (кроме зон, где флаг снят по таймеру)."""
    if sys.platform != "win32":
        return
    import ctypes
    hwnd = int(widget.winId())
    gwl_exstyle = -20
    ws_ex_transparent = 0x20
    style = ctypes.windll.user32.GetWindowLongW(hwnd, gwl_exstyle)
    if enabled:
        style |= ws_ex_transparent
    else:
        style &= ~ws_ex_transparent
    ctypes.windll.user32.SetWindowLongW(hwnd, gwl_exstyle, style)
