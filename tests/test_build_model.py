from actpilot.build_model import (
    duplicate_link, move_gem, reorder_links, unknown_tree_nodes,
)
from actpilot.gems.data import link_to_text, links_to_text


def gem(name, support=False):
    return {"name": name, "support": support, "level": "20", "quality": "0"}


def links():
    return [
        {"label": "Body Armour", "gems": [gem("Freezing Pulse"), gem("Arcane Surge", True)]},
        {"label": "Gloves", "gems": [gem("Frostbolt")]},
    ]


def names(link):
    return [item["name"] for item in link["gems"]]


def test_link_to_text():
    assert link_to_text(links()[0]) == "Freezing Pulse, Arcane Surge"
    assert link_to_text({"gems": []}) == ""
    assert link_to_text(None) == ""


def test_links_to_text_skips_empty():
    data = links() + [{"label": "Пустая", "gems": []}]
    assert links_to_text(data) == "Freezing Pulse, Arcane Surge\nFrostbolt"


def test_duplicate_link_inserts_independent_copy():
    data = links()
    position = duplicate_link(data, 0)
    assert position == 1
    assert len(data) == 3
    assert names(data[1]) == ["Freezing Pulse", "Arcane Surge"]
    data[1]["gems"][0]["name"] = "Changed"
    assert names(data[0]) == ["Freezing Pulse", "Arcane Surge"]


def test_duplicate_link_rejects_bad_index():
    data = links()
    assert duplicate_link(data, 9) == -1
    assert duplicate_link([], 0) == -1
    assert len(data) == 2


def test_reorder_links():
    data = links()
    assert reorder_links(data, 1, 0) == 0
    assert [link["label"] for link in data] == ["Gloves", "Body Armour"]
    assert reorder_links(data, 0, 99) == 1
    assert [link["label"] for link in data] == ["Body Armour", "Gloves"]
    assert reorder_links(data, 5, 0) == -1


def test_move_gem_between_links():
    data = links()
    assert move_gem(data, 0, 1, 1) == 1
    assert names(data[0]) == ["Freezing Pulse"]
    assert names(data[1]) == ["Frostbolt", "Arcane Surge"]


def test_move_gem_inside_link_keeps_count():
    data = links()
    assert move_gem(data, 0, 0, 0, 2) == 1
    assert names(data[0]) == ["Arcane Surge", "Freezing Pulse"]


def test_move_gem_rejects_bad_input():
    data = links()
    assert move_gem(data, 0, 7, 1) == -1
    assert move_gem(data, 3, 0, 1) == -1
    assert names(data[0]) == ["Freezing Pulse", "Arcane Surge"]


def test_unknown_tree_nodes_ignores_cluster_jewel_nodes():
    build = {"trees": [{"tree_version": "3_26", "nodes": [123, 456, 65600, 70000]}]}
    missing, version = unknown_tree_nodes(build)
    assert (missing, version) == (2, "3.26")


def test_unknown_tree_nodes_without_trees():
    assert unknown_tree_nodes({}) == (0, "")
