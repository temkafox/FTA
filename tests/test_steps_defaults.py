from actpilot.steps import (
    DEFAULT_STEPS, GAME_POE1, GAME_POE2, get_user_steps_file,
)


def test_default_steps_loaded_from_bundle():
    assert DEFAULT_STEPS, "дефолтные шаги должны читаться из bundled steps.json"
    assert [f"Act {i}" for i in range(1, 11)] == list(DEFAULT_STEPS.keys())
    assert all(isinstance(v, list) and v for v in DEFAULT_STEPS.values())


def test_user_steps_file_naming():
    assert get_user_steps_file(GAME_POE1).name == "steps_poe1.json"
    assert get_user_steps_file(GAME_POE2).name == "steps_poe2.json"
