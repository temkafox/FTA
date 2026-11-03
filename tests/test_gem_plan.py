import copy

from actpilot.gems.plan import (
    act_items, annotate_links, build_gem_plan, campaign_act, gem_key, known_keys,
    plan_badges, plan_gems, plan_lines, required_gems,
)

DATA = {
    "classes": ["Templar", "Witch"],
    "start_gems": {"Witch": {"start": "fireball", "chest": "arcane surge support"}},
    "quests": [
        {"id": "q1", "act": 1, "name": "Enemy at the Gate", "offers": [
            {"npc": "Tarkleigh", "rewards": {"rolling magma": ["Witch"]},
             "vendor": {"rolling magma": {"npc": "Nessa", "classes": ["Witch"]}}},
        ]},
        {"id": "q2", "act": 1, "name": "The Caged Brute", "offers": [
            {"npc": "Nessa",
             "rewards": {"added lightning damage support": ["Witch"], "minion damage support": ["Witch"]},
             "vendor": {
                 "added lightning damage support": {"npc": "Nessa", "classes": ["Witch"]},
                 "minion damage support": {"npc": "Nessa", "classes": ["Witch"]},
                 "void manipulation support": {"npc": "Nessa", "classes": ["Templar", "Witch"]},
             }},
            {"npc": "Tarkleigh", "rewards": {"clarity": ["Witch"]}, "vendor": {}},
        ]},
        {"id": "q3", "act": 6, "name": "Fallen from Grace", "offers": [
            {"npc": "", "rewards": {}, "vendor": {
                "void manipulation support": {"npc": "Lilly Roth", "classes": ["Templar", "Witch"]},
                "meat shield support": {"npc": "Lilly Roth", "classes": ["Templar", "Witch"]},
            }},
        ]},
    ],
    "gems": {key: {} for key in (
        "rolling magma", "added lightning damage support", "minion damage support", "clarity",
        "void manipulation support", "meat shield support", "summon holy relic", "arcane surge support",
    )},
}


def need(name, level=1, count=1, support=False):
    return {"key": gem_key(name, support, known_keys(DATA)), "name": name, "support": support,
            "level": level, "count": count}


def plan_for(*needed, class_name="Witch"):
    return plan_gems(list(needed), class_name, DATA)


def kinds(plan, name, support=False):
    info = plan["gems"][gem_key(name, support, known_keys(DATA))]
    return [(action["kind"], action.get("npc"), action["count"]) for action in info["actions"]]


def test_first_needed_gem_is_the_free_reward_and_the_rest_is_bought():
    plan = plan_for(need("Added Lightning Damage", 8, support=True), need("Minion Damage", 8, support=True))
    assert kinds(plan, "Added Lightning Damage", True) == [("reward", "Nessa", 1)]
    assert kinds(plan, "Minion Damage", True) == [("buy", "Nessa", 1)]


def test_second_reward_offer_of_a_quest_is_used_too():
    plan = plan_for(need("Added Lightning Damage", 8, support=True), need("Clarity", 10))
    assert kinds(plan, "Clarity") == [("reward", "Tarkleigh", 1)]


def test_chest_gem_is_owned_from_the_start():
    plan = plan_for(need("Arcane Surge", support=True))
    assert kinds(plan, "Arcane Surge", True) == [("chest", None, 1)]


def test_late_purchase_moves_to_the_last_vendor():
    plan = plan_for(need("Void Manipulation", 68, support=True))
    action = plan["gems"]["void manipulation support"]["actions"][0]
    assert (action["kind"], action["npc"], action["act"], action["deferred"]) == ("buy", "Lilly Roth", 6, True)
    assert "нужен с ур. 68" in plan_lines(plan["gems"]["void manipulation support"])[0]


def test_soon_needed_purchase_is_not_deferred():
    plan = plan_for(need("Void Manipulation", 12, support=True))
    action = plan["gems"]["void manipulation support"]["actions"][0]
    assert (action["npc"], action["deferred"]) == ("Nessa", False)


def test_copies_after_reward_are_bought():
    plan = plan_for(need("Rolling Magma", 1, count=2))
    assert kinds(plan, "Rolling Magma") == [("reward", "Tarkleigh", 1), ("buy", "Nessa", 1)]


def test_rewards_respect_class():
    plan = plan_for(need("Rolling Magma"), class_name="Templar")
    assert plan["gems"]["rolling magma"]["actions"] == []
    assert plan["gems"]["rolling magma"]["missing"]["reason"] == "trade"


def test_transfigured_gem_points_to_divine_font():
    plan = plan_for(need("Summon Holy Relic of Conviction", 68))
    assert plan["unavailable"][0]["reason"] == "divine_font"
    assert plan["unavailable"][0]["base"] == "Summon Holy Relic"


def test_act_items_skip_deferred_purchases():
    plan = plan_for(need("Rolling Magma"), need("Void Manipulation", 68, support=True))
    assert [(gem["name"], letter) for gem, letter in act_items(plan, 1)] == [("Rolling Magma", "Q")]
    assert act_items(plan, 6) == []


def test_plan_badges_follow_the_plan():
    plan = plan_for(
        need("Rolling Magma", 1, count=2),
        need("Added Lightning Damage", 8, support=True),
        need("Minion Damage", 8, support=True),
    )
    links = annotate_links([{"gems": [
        {"name": "Rolling Magma", "support": False}, {"name": "Minion Damage", "support": True},
    ]}], plan)
    assert [plan_badges(gem, "Witch") for gem in links[0]["gems"]] == ["QB", "B"]


def test_annotate_links_keeps_input_untouched():
    links = [{"gems": [{"name": "Rolling Magma", "support": False}]}]
    original = copy.deepcopy(links)
    annotate_links(links, plan_for(need("Rolling Magma")))
    assert links == original


def test_required_gems_order_copies_and_level():
    build = {"gem_sets": [
        {"level": 12, "links": [{"gems": [
            {"name": "Meat Shield", "support": True}, {"name": "Meat Shield", "support": True},
            {"name": "Primal Aegis", "support": False},
        ]}]},
        {"level": 1, "links": [{"gems": [{"name": "Spell Echo", "support": True}]}]},
    ]}
    needed = required_gems(build)
    assert [(item["name"], item["count"], item["level"]) for item in needed] == [
        ("Spell Echo", 1, 38), ("Meat Shield", 2, 31),
    ]


def test_campaign_act_prefers_step_then_level():
    assert campaign_act("Act 3", 60) == 3
    assert campaign_act("", 30) == 3
    assert campaign_act("Мой акт", 5) == 1
    assert campaign_act("", 80) is None


def test_build_plan_needs_known_class():
    build = {"class": "", "gem_sets": [{"level": 1, "links": [{"gems": [{"name": "Arc"}]}]}]}
    assert build_gem_plan(build) is None


def test_witch_plan_on_real_data():
    build = {"class": "Witch", "gem_sets": [{"level": 1, "links": [{"gems": [
        {"name": "Rolling Magma", "support": False}, {"name": "Arcane Surge", "support": True},
        {"name": "Absolution", "support": False}, {"name": "Flesh Offering", "support": False},
        {"name": "Spell Echo", "support": True},
        {"name": "Summon Holy Relic of Conviction", "support": False},
    ]}]}]}
    plan = build_gem_plan(build)
    lines = {info["name"]: plan_lines(info)[0] for info in plan["gems"].values()}
    assert lines["Arcane Surge"] == "Сундук на Twilight Strand · Акт 1"
    assert lines["Rolling Magma"].startswith("Награда за Enemy at the Gate")
    assert lines["Absolution"] == "Купить у Nessa после The Siren's Cadence · Акт 1"
    assert lines["Flesh Offering"].startswith("Награда за The Siren's Cadence")
    assert lines["Spell Echo"].startswith("Награда за The Eternal Nightmare")
    assert lines["Summon Holy Relic of Conviction"].startswith("Divine Font")
