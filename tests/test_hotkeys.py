from PyQt5.QtCore import Qt

import main
from actpilot.settings_dialog import capture_hotkey


def test_normalize_fkeys():
    assert main.normalize_hotkey("F4") == "<f4>"
    assert main.normalize_hotkey(" f10 ") == "<f10>"


def test_normalize_combo():
    assert main.normalize_hotkey("ctrl+shift+p") == "<ctrl>+<shift>+p"
    assert main.normalize_hotkey("Ctrl+F3") == "<ctrl>+<f3>"


def test_normalize_empty_falls_back_to_f4():
    assert main.normalize_hotkey("") == "<f4>"


def test_display_hotkey():
    assert main.display_hotkey("<f3>") == "F3"
    assert main.display_hotkey("<ctrl>+<f3>") == "Ctrl+F3"
    assert main.display_hotkey("<ctrl>+<shift>+p") == "Ctrl+Shift+P"


def test_capture_accepts_fkeys():
    assert capture_hotkey(Qt.Key_F3, Qt.NoModifier) == "F3"
    assert capture_hotkey(Qt.Key_F12, Qt.ControlModifier) == "Ctrl+F12"
    assert capture_hotkey(Qt.Key_F1, Qt.ControlModifier | Qt.ShiftModifier) == "Ctrl+Shift+F1"


def test_capture_accepts_alnum_with_ctrl_or_alt():
    assert capture_hotkey(Qt.Key_P, Qt.ControlModifier) == "Ctrl+P"
    assert capture_hotkey(Qt.Key_1, Qt.AltModifier) == "Alt+1"


def test_capture_rejects_bare_game_keys():
    assert capture_hotkey(Qt.Key_W, Qt.NoModifier) is None
    assert capture_hotkey(Qt.Key_1, Qt.NoModifier) is None
    assert capture_hotkey(Qt.Key_W, Qt.ShiftModifier) is None


def test_capture_rejects_named_keys_and_win():
    assert capture_hotkey(Qt.Key_Space, Qt.NoModifier) is None
    assert capture_hotkey(Qt.Key_Return, Qt.ControlModifier) is None
    assert capture_hotkey(Qt.Key_Left, Qt.NoModifier) is None
    assert capture_hotkey(Qt.Key_F3, Qt.MetaModifier) is None


def test_captured_combos_survive_normalize_round_trip():
    for combo in ("F3", "Ctrl+F12", "Ctrl+P", "Alt+1", "Ctrl+Shift+F1"):
        normalized = main.normalize_hotkey(combo)
        assert "<" in normalized
        assert main.display_hotkey(normalized).lower() == combo.lower()
