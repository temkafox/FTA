import base64
import zlib

import pytest

from actpilot import builds


MINIMAL_XML = (
    '<PathOfBuilding><Build level="42" className="Witch" ascendClassName="Necromancer"/>'
    '<Tree activeSpec="1"><Spec title="lvl 42" nodes="1,2,3"/></Tree>'
    "</PathOfBuilding>"
)


def encode_pob(xml_text: str) -> str:
    return base64.urlsafe_b64encode(zlib.compress(xml_text.encode("utf-8"))).decode("ascii")


def test_decode_raw_xml_passthrough():
    assert builds.decode_pob_xml(MINIMAL_XML) == MINIMAL_XML


def test_decode_pob_code_round_trip():
    assert builds.decode_pob_xml(encode_pob(MINIMAL_XML)) == MINIMAL_XML


def test_decode_rejects_urls():
    with pytest.raises(builds.PobImportError):
        builds.decode_pob_xml("https://pobb.in/abcdef")


def test_decode_rejects_garbage():
    with pytest.raises(builds.PobImportError):
        builds.decode_pob_xml("явно не код")


def test_decode_rejects_empty():
    with pytest.raises(builds.PobImportError):
        builds.decode_pob_xml("   ")


def test_parse_pob_minimal():
    parsed = builds.parse_pob(encode_pob(MINIMAL_XML))
    assert parsed["character_level"] == 42
    assert parsed["class"] == "Witch"
    assert parsed["ascendancy"] == "Necromancer"


def test_parse_pob_rejects_foreign_xml():
    with pytest.raises(builds.PobImportError):
        builds.parse_pob("<NotPob/>")


EXPORT_XML = (
    '<PathOfBuilding>'
    '<Build level="42" className="Witch" ascendClassName="Necromancer"/>'
    '<Tree activeSpec="2">'
    '<Spec title="Level 12" treeVersion="3_26" nodes="57560,57264"/>'
    '<Spec title="80 points" treeVersion="3_26" nodes="57560,57264,4"/>'
    '</Tree>'
    '<Skills activeSkillSet="2">'
    '<SkillSet id="1" title="Leveling">'
    '<Skill enabled="true" slot="Body Armour">'
    '<Gem nameSpec="Freezing Pulse" skillId="FreezingPulse"'
    ' gemId="Metadata/Items/Gems/SkillGemFreezingPulse" level="1" enabled="true"/>'
    '<Gem nameSpec="Added Lightning Damage" skillId="SupportAddedLightningDamage"'
    ' gemId="Metadata/Items/Gems/SupportGemAddedLightningDamage" level="1" enabled="true"/>'
    '<Gem nameSpec="Chance to Flee" skillId="SupportChanceToFlee" level="1" enabled="false"/>'
    '</Skill>'
    '<Skill enabled="true" source="Item:1:Glorious Vanity">'
    '<Gem nameSpec="Primal Aegis" skillId="PrimalAegis" level="1" enabled="true"/>'
    '</Skill>'
    '</SkillSet>'
    '<SkillSet id="2" title="Endgame">'
    '<Skill enabled="true" slot="Weapon 1">'
    '<Gem nameSpec="Anger" skillId="Anger"'
    ' gemId="Metadata/Items/Gems/SkillGemAnger" level="20" enabled="true"/>'
    '</Skill>'
    '</SkillSet>'
    '</Skills>'
    '</PathOfBuilding>'
)


def parsed_export():
    return builds.parse_pob(EXPORT_XML)


def test_support_flag_comes_from_skill_id():
    gems = parsed_export()["gem_sets"][0]["links"][0]["gems"]
    assert [(gem["name"], gem["support"]) for gem in gems] == [
        ("Freezing Pulse", False),
        ("Added Lightning Damage", True),
    ]


def test_item_granted_skills_are_skipped():
    links = parsed_export()["gem_sets"][0]["links"]
    assert [link["label"] for link in links] == ["Body Armour"]


def test_active_skill_set_and_spec_are_marked():
    build = parsed_export()
    assert [item["active"] for item in build["gem_sets"]] == [False, True]
    assert [item["active"] for item in build["trees"]] == [False, True]


def test_missing_title_level_is_marked_as_guessed():
    build = parsed_export()
    assert [item["level_guessed"] for item in build["gem_sets"]] == [True, True]
    assert [item["level_guessed"] for item in build["trees"]] == [False, False]


def test_level_from_title():
    assert builds.level_from_title("Уровень 25") == 25
    assert builds.level_from_title("lvl: 60") == 60
    assert builds.level_from_title("без числа", fallback=7) == 7
    assert builds.level_from_title("без числа") is None


def test_level_from_title_reads_range_start():
    assert builds.level_from_title("12-28") == 12
    assert builds.level_from_title("Уровень 12-28") == 12


def test_level_from_title_ignores_names_with_numbers():
    assert builds.level_from_title("Act 4") is None
    assert builds.level_from_title("Ice Nova 2") is None
    assert builds.level_from_title("Boss setup 3", fallback=30) == 30


def test_level_from_title_converts_passive_points():
    assert builds.level_from_title("80 points") == 80 - builds.QUEST_PASSIVE_POINTS
    assert builds.level_from_title("31 очко") == 31 - builds.QUEST_PASSIVE_POINTS


def test_level_from_title_reads_bare_number():
    assert builds.level_from_title("42") == 42


def test_clamp_level():
    assert builds.clamp_level(0) == 1
    assert builds.clamp_level(101) == 100
    assert builds.clamp_level("55") == 55
    assert builds.clamp_level("мусор") == 1
