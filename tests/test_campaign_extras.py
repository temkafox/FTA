import pytest
from PyQt5.QtWidgets import QApplication

from actpilot.steps import GAME_POE1, GAME_POE2, campaign_extras
from actpilot.widgets import ContentArea
from tools.update_campaign_extras import build_extras, translate_recipe


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_translate_recipe_families_and_details():
    assert translate_recipe("Physical Damage - Rank 3") == ("Физический урон, ранг 3", True)
    assert translate_recipe("Socket Links - 2 to 4 Linked Sockets") == ("Связи гнёзд, 2–4 связанных гнезда", True)
    assert translate_recipe("Socket Colours") == ("Цвета гнёзд", True)
    assert translate_recipe("Brand New Family - Rank 1") == ("Brand New Family - Rank 1", False)


def test_build_extras_places_labs_epilogue_and_reports_problems():
    areas = {
        "1_Labyrinth_boss_3": {"name": "Aspirant's Trial", "act": 3, "crafting_recipes": ["All Resistances - Rank 1"]},
        "EndGame_Labyrinth_boss_3": {"name": "Aspirant's Trial", "act": 11, "crafting_recipes": ["All Resistances - Rank 2"]},
        "2_11_endgame_town": {"name": "Karui Shores", "act": 11, "crafting_recipes": ["Movement Speed - Rank 3"]},
        "2_9_8": {"name": "The Quarry", "act": 9, "crafting_recipes": ["Physical Damage - Rank 3"]},
        "2_9_9": {"name": "The Refinery", "act": 9, "crafting_recipes": ["Mystery - Rank 1"]},
    }
    payload, problems = build_extras(areas, {"The Quarry": "Каменоломня", "Karui Shores": "Берега Каруи"}, "test")
    recipes = {act: [item["text"] for item in items if item["kind"] == "recipe"] for act, items in payload["acts"].items()}
    assert recipes["Act 4"] == ["ЛАБИРИНТ (сокровищница Изаро): Сопротивление всем стихиям, ранг 1"]
    assert recipes["Act 10"] == ["БЕРЕГА КАРУИ: Скорость передвижения, ранг 3"]
    assert recipes["Act 9"][0] == "КАМЕНОЛОМНЯ: Физический урон, ранг 3"
    assert "рецепт не переведён: Mystery - Rank 1" in problems
    assert "нет русского названия: The Refinery" in problems


def test_bundled_extras_shape():
    extras = campaign_extras(GAME_POE1)
    assert set(extras) == {f"Act {act}" for act in range(1, 11)}
    kinds = {item["kind"] for items in extras.values() for item in items}
    assert kinds == {"recipe", "secret", "optional"}
    assert any("ФАБРИКА" in item["text"] and "Trigger" in item["text"] for item in extras["Act 9"])
    assert campaign_extras(GAME_POE2) == {}


def make_content(extras):
    content = ContentArea()
    content.set_extras(extras)
    content.load({"Act 1": ["a", "b"], "Act 2": ["c"]})
    return content


def test_extras_stay_outside_progress(qapp):
    content = make_content({"Act 1": [{"kind": "recipe", "text": "X: y"}]})
    assert [step.text for step in content.all_steps] == ["a", "b", "c"]
    content._on_click(content.all_steps[1])
    assert content.groups[0].is_completed()
    assert content.all_steps[content.current_index].text == "c"


def test_extras_block_is_collapsed_and_toggles(qapp):
    content = make_content({"Act 1": [{"kind": "secret", "text": "тайник"}, {"kind": "recipe", "text": "рецепт"}]})
    group = content.groups[0]
    assert group.extras_list.isHidden()
    assert "Дополнительно · 2" in group.extras_toggle.text()
    group.toggle_extras()
    assert not group.extras_list.isHidden()
    assert content.groups[1].extras_block is None


def test_show_extras_setting_hides_blocks(qapp):
    content = make_content({"Act 1": [{"kind": "optional", "text": "x"}]})
    content.set_show_extras(False)
    assert content.groups[0].extras_block.isHidden()
    content.load({"Act 1": ["a"]})
    assert content.groups[0].extras_block.isHidden()
