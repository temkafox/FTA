from actpilot.shared import migrate_settings


def test_adds_new_keys_to_old_settings():
    settings = {"hotkey": "<f8>", "layout_hotkey": "<f9>"}
    assert migrate_settings(settings)
    assert settings["previous_hotkey"] == "<ctrl>+<f3>"
    assert settings["regex_hotkey"] == "<f6>"
    assert settings["regexes"]
    assert settings["hotkey_defaults_version"] == 2
    assert settings["regex_defaults_version"] == 2
    assert settings["show_step_splits"] is True


def test_preserves_user_hotkeys():
    settings = {"hotkey": "<f8>", "layout_hotkey": "<f9>", "previous_hotkey": "<ctrl>+p"}
    migrate_settings(settings)
    assert settings["hotkey"] == "<f8>"
    assert settings["layout_hotkey"] == "<f9>"
    assert settings["previous_hotkey"] == "<ctrl>+p"


def test_preserves_user_regexes():
    entries = [{"name": "мой", "pattern": "x-x"}]
    settings = {"regexes": entries}
    migrate_settings(settings)
    assert settings["regexes"] is entries


def test_idempotent():
    settings = {}
    assert migrate_settings(settings)
    snapshot = dict(settings)
    assert not migrate_settings(settings)
    assert settings == snapshot


def test_defaults_are_not_shared_reference():
    first, second = {}, {}
    migrate_settings(first)
    migrate_settings(second)
    first["regexes"][0]["name"] = "изменено"
    assert second["regexes"][0]["name"] != "изменено"
