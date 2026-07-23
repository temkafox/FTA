from actpilot.steps import (
    DEFAULT_STEPS, GAME_POE1, GAME_POE2, get_user_steps_file, normalize_steps,
)


def test_default_steps_loaded_from_bundle():
    assert DEFAULT_STEPS, "дефолтные шаги должны читаться из bundled steps.json"
    assert [f"Act {i}" for i in range(1, 11)] == list(DEFAULT_STEPS.keys())
    assert all(isinstance(v, list) and v for v in DEFAULT_STEPS.values())


def test_user_steps_file_naming():
    assert get_user_steps_file(GAME_POE1).name == "steps_poe1.json"
    assert get_user_steps_file(GAME_POE2).name == "steps_poe2.json"


def test_normalize_assigns_ids_to_strings():
    data, added = normalize_steps({"Act 1": ["a", "b"]})
    assert added is True
    assert all(s["id"] and s["text"] for s in data["Act 1"])
    ids = [s["id"] for s in data["Act 1"]]
    assert len(set(ids)) == len(ids)  # уникальны


def test_normalize_idempotent_on_objects():
    first, _ = normalize_steps({"Act 1": ["a", "b"]})
    second, added = normalize_steps(first)
    assert added is False
    assert [s["id"] for s in second["Act 1"]] == [s["id"] for s in first["Act 1"]]


def test_normalize_coerces_mixed_and_keeps_existing_id():
    data, added = normalize_steps({"Act 1": [{"id": "X", "text": "a"}, "b"]})
    assert added is True  # строка 'b' получила id
    assert data["Act 1"][0] == {"id": "X", "text": "a"}
    assert data["Act 1"][1]["id"] and data["Act 1"][1]["text"] == "b"


def test_normalize_handles_empty():
    data, added = normalize_steps({})
    assert data == {} and added is False


def test_persist_writes_to_resolved_path(tmp_path, monkeypatch):
    import json

    from actpilot import steps as steps_mod

    resolved = tmp_path / "steps_poe1.json"
    monkeypatch.setattr(steps_mod, "get_user_steps_file", lambda g: tmp_path / "user.json")
    monkeypatch.setattr(steps_mod, "get_bundled_steps_file", lambda g: tmp_path / "bundled.json")
    data, _ = steps_mod.normalize_steps({"Act 1": ["a"]})
    steps_mod.persist_steps_with_ids("poe1", resolved, data)
    assert json.loads(resolved.read_text(encoding="utf-8"))["Act 1"][0]["text"] == "a"


def test_persist_bundle_source_redirects_to_user(tmp_path, monkeypatch):
    from actpilot import steps as steps_mod

    bundled = tmp_path / "bundled.json"
    user = tmp_path / "user.json"
    monkeypatch.setattr(steps_mod, "get_user_steps_file", lambda g: user)
    monkeypatch.setattr(steps_mod, "get_bundled_steps_file", lambda g: bundled)
    data, _ = steps_mod.normalize_steps({"Act 1": ["a"]})
    steps_mod.persist_steps_with_ids("poe1", bundled, data)  # источник — read-only бандл
    assert user.exists() and not bundled.exists()
