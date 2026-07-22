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


def test_level_from_title():
    assert builds.level_from_title("Уровень 25") == 25
    assert builds.level_from_title("lvl: 60") == 60
    assert builds.level_from_title("без числа", fallback=7) == 7
    assert builds.level_from_title("без числа") is None


def test_clamp_level():
    assert builds.clamp_level(0) == 1
    assert builds.clamp_level(101) == 100
    assert builds.clamp_level("55") == 55
    assert builds.clamp_level("мусор") == 1
