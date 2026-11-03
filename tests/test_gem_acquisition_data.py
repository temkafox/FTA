from actpilot.data_cache import game_data
from actpilot.gems.data import acquisition_for
from tools.update_gem_acquisition import convert

DATA = game_data("gem_acquisition.json")
ALL = ["Duelist", "Marauder", "Ranger", "Scion", "Shadow", "Templar", "Witch"]


def raw_input():
    gems = {
        "Gems/Arc": {"name": "Arc"},
        "Gems/ArcticOld": {"name": "Arctic Armour"},
        "Gems/ArcticNew": {"name": "Arctic Armour"},
        "Gems/ArcRoyale": {"name": "Arc"},
        "Gems/SupportFaster": {"name": "Faster Attacks Support"},
    }
    quests = {
        "a1q1": {"id": "a1q1", "name": "First", "act": "1", "reward_offers": {
            "a1q1": {"quest_npc": "Tarkleigh",
                     "quest": {"Gems/Arc": {"classes": ["Witch"]}, "Flasks/Life": {"classes": []}},
                     "vendor": {"Gems/SupportFaster": {"classes": [], "npc": "Nessa"}}},
        }},
        "a1q2": {"id": "a1q2", "name": "Flasks only", "act": "1", "reward_offers": {
            "a1q2": {"quest_npc": "Nessa", "quest": {"Flasks/Life": {"classes": []}}, "vendor": {}},
        }},
        "a2q1": {"id": "a2q1", "name": "Second", "act": "2", "reward_offers": {
            "a2q1": {"quest_npc": "Greust",
                     "quest": {"Gems/ArcticOld": {"classes": ["Witch"]}, "Gems/ArcticNew": {"classes": ["Templar"]},
                               "Gems/ArcRoyale": {"classes": ["Shadow"]}},
                     "vendor": {}},
        }},
    }
    characters = {name: {} for name in ALL}
    characters["Witch"] = {"start_gem_id": "Gems/Arc", "chest_gem_id": "Gems/SupportFaster"}
    return quests, gems, characters


def test_convert_expands_empty_classes_to_all():
    data = convert(*raw_input(), ref="test")
    vendor = data["quests"][0]["offers"][0]["vendor"]
    assert vendor["faster attacks support"] == {"npc": "Nessa", "classes": ALL}


def test_convert_merges_ids_and_skips_royale_and_items():
    data = convert(*raw_input(), ref="test")
    assert [quest["name"] for quest in data["quests"]] == ["First", "Second"]
    rewards = data["quests"][1]["offers"][0]["rewards"]
    assert rewards == {"arctic armour": ["Templar", "Witch"]}
    assert data["quests"][0]["offers"][0]["rewards"] == {"arc": ["Witch"]}


def test_convert_builds_start_gems_and_legacy_index():
    data = convert(*raw_input(), ref="test")
    assert data["start_gems"]["Witch"] == {"start": "arc", "chest": "faster attacks support"}
    assert data["gems"]["arc"]["classes"]["Witch"]["quest"] == [{"act": 1, "quest": "First"}]
    assert data["gems"]["faster attacks support"]["classes"]["Templar"]["vendor"] == [
        {"act": 1, "quest": "First", "npc": "Nessa"}
    ]


def witch_offer(quest_name, key):
    quest = next(item for item in DATA["quests"] if item["name"] == quest_name)
    rewards = [offer["rewards"].get(key, []) for offer in quest["offers"]]
    vendors = [offer["vendor"].get(key, {}) for offer in quest["offers"]]
    return any("Witch" in item for item in rewards), [v["npc"] for v in vendors if "Witch" in v.get("classes", [])]


def test_bundled_data_shape():
    assert DATA["format"] == 2
    assert DATA["classes"] == ALL
    assert DATA["quests"][0]["name"] == "Enemy at the Gate"
    assert DATA["start_gems"]["Witch"]["chest"] == "arcane surge support"


def test_bundled_data_3_29_facts_for_witch():
    assert witch_offer("The Siren's Cadence", "flesh offering") == (True, ["Nessa"])
    assert witch_offer("The Siren's Cadence", "bone offering") == (False, ["Nessa"])
    assert witch_offer("The Caged Brute", "faster attacks support")[1] == ["Nessa"]
    assert witch_offer("Fallen from Grace", "withering touch support")[1] == ["Lilly Roth"]
    assert "tempest shield" in DATA["gems"]


def test_legacy_lookup_sees_new_gems():
    ways = acquisition_for("Flesh Offering", "Witch")
    assert {"act": 1, "quest": "The Siren's Cadence"} in ways["quest"]
