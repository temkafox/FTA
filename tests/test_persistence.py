import json

import main


def test_round_trip(tmp_path):
    path = tmp_path / "settings.json"
    data = {"hotkey": "F3", "кириллица": [1, 2, 3]}
    main.save_json(path, data)
    assert json.loads(path.read_text(encoding="utf-8")) == data
    assert main.load_json(path, {}) == data


def test_atomic_no_tmp_left(tmp_path):
    path = tmp_path / "x.json"
    main.save_json(path, {"a": 1})
    assert not list(tmp_path.glob("*.tmp"))


def test_creates_parent_dirs(tmp_path):
    path = tmp_path / "nested" / "deep" / "x.json"
    main.save_json(path, {"a": 1})
    assert json.loads(path.read_text(encoding="utf-8")) == {"a": 1}


def test_corrupt_file_returns_default_and_quarantines(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("{broken", encoding="utf-8")
    default = {"game": "poe1"}
    result = main.load_json(path, default)
    assert result == default
    assert result is not default
    assert not path.exists()
    assert (tmp_path / "settings.json.corrupt").exists()


def test_missing_file_returns_default_copy(tmp_path):
    default = {"a": 1}
    result = main.load_json(tmp_path / "nope.json", default)
    assert result == default
    assert result is not default


def test_overwrite(tmp_path):
    path = tmp_path / "s.json"
    main.save_json(path, {"v": 1})
    main.save_json(path, {"v": 2})
    assert main.load_json(path, {}) == {"v": 2}
