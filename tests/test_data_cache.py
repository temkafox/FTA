import actpilot.data_cache as dc


def test_load_file_parsed_once_same_object(tmp_path):
    f = tmp_path / "x.json"
    f.write_text('{"a": 1}', encoding="utf-8")
    first = dc.load_file(f)
    second = dc.load_file(f)
    assert first is second
    assert first == {"a": 1}


def test_load_file_missing_returns_default(tmp_path):
    assert dc.load_file(tmp_path / "nope.json", {"d": 1}) == {"d": 1}
    assert dc.load_file(tmp_path / "nope.json") == {}


def test_tree_graph_cached_and_correct(tmp_path):
    f = tmp_path / "tree.json"
    f.write_text(
        '{"nodes": {"1": {"out": ["2"], "in": []}, "2": {"out": [], "in": ["1"]},'
        ' "3": {"out": ["999"], "in": []}}}',
        encoding="utf-8",
    )
    first = dc.tree_graph(f)
    second = dc.tree_graph(f)
    assert first is second
    assert first["1"] == {"2"}
    assert first["2"] == {"1"}
    assert first["3"] == set()


def test_tree_graph_matches_legacy_build_adjacency(tmp_path):
    from actpilot.progression import build_adjacency

    f = tmp_path / "tree.json"
    f.write_text(
        '{"nodes": {"10": {"out": ["20", "30"], "in": []}, "20": {"out": [], "in": ["10"]},'
        ' "30": {"out": ["20"], "in": []}}}',
        encoding="utf-8",
    )
    assert dc.tree_graph(f) == build_adjacency(f)


def test_tree_graph_missing_file(tmp_path):
    assert dc.tree_graph(tmp_path / "absent.json") == {}
