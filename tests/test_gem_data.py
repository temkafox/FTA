import pytest

from actpilot.gems.data import (
    acquisition_for, badges_for, is_support_gem, links_at_level, locked_gems,
    required_level,
)


def gem(name, support=False, level="20"):
    return {"name": name, "support": support, "level": level, "quality": "0"}


def links():
    return [
        {
            "label": "A",
            "gems": [
                gem("Freezing Pulse"),
                gem("Added Lightning Damage", True),
                gem("Hypothermia", True),
                gem("Primal Aegis"),
            ],
        }
    ]


def names(link):
    return [item["name"] for item in link["gems"]]


def test_support_gem_is_found_without_suffix():
    """Path of Building пишет «Added Fire Damage», справочник — «... Support»."""
    ways = acquisition_for("Added Fire Damage", "Marauder", support=True)
    assert ways["quest"] or ways["vendor"]
    assert badges_for("Added Fire Damage", "Marauder", True)


def test_support_gem_is_found_without_type_hint():
    assert badges_for("Added Fire Damage", "Marauder") == badges_for(
        "Added Fire Damage", "Marauder", True
    )


def test_suffixed_name_still_works():
    assert badges_for("Added Fire Damage Support", "Marauder", True) == badges_for(
        "Added Fire Damage", "Marauder", True
    )


def test_active_gem_lookup_is_unchanged():
    assert badges_for("Freezing Pulse", "Witch", False) == "QB"


def test_unknown_gem_has_no_badges():
    assert badges_for("Совершенно неизвестный камень", "Witch") == ""


def test_required_level():
    assert required_level("Freezing Pulse") == 1
    assert required_level("Hypothermia") == 31
    assert required_level("нет такого") is None


def test_links_at_level_hides_unavailable_gems():
    assert names(links_at_level(links(), 1)[0]) == ["Freezing Pulse", "Primal Aegis"]
    assert names(links_at_level(links(), 8)[0]) == [
        "Freezing Pulse", "Added Lightning Damage", "Primal Aegis",
    ]


def test_links_at_level_scales_gem_level():
    gems = links_at_level([{"gems": [gem("Freezing Pulse")]}], 10)[0]["gems"]
    assert int(gems[0]["level"]) < 20


def test_locked_gems_lists_nearest_first():
    assert locked_gems(links(), 1) == [("Added Lightning Damage", 8), ("Hypothermia", 31)]
    assert locked_gems(links(), 8) == [("Hypothermia", 31)]
    assert locked_gems(links(), 31) == []


def test_locked_gems_ignores_skills_granted_by_items():
    assert locked_gems([{"gems": [gem("Primal Aegis")]}], 1) == []


@pytest.mark.parametrize(
    "name, support",
    [
        ("Added Fire Damage", True),
        ("Controlled Destruction", True),
        ("Hypothermia", True),
        ("Freezing Pulse", False),
        ("Anger", False),
        ("Vaal Righteous Fire", False),
        # Имя есть и у умения, и у камня поддержки: различает только суффикс
        ("Barrage", False),
        ("Barrage Support", True),
        ("", False),
        ("Неизвестный камень", False),
    ],
)
def test_is_support_gem(name, support):
    assert is_support_gem(name) is support
