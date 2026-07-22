import poe1_client_log_v2 as clientlog


def test_parse_level_event_en():
    line = "2026/07/21 20:00:00 123 abc [INFO Client 1] : Exile (Witch) is now level 12"
    events = clientlog.parse_level_events(line)
    assert events == [clientlog.LevelEvent(name="Exile", character_class="Witch", level=12)]


def test_parse_level_event_ru():
    line = "2026/07/21 20:00:00 123 abc [INFO Client 1] : Иона (Ведьма) достигает 34 уровня"
    events = clientlog.parse_level_events(line)
    assert events == [clientlog.LevelEvent(name="Иона", character_class="Ведьма", level=34)]


def test_parse_strips_nul_and_ignores_chat():
    text = (
        "\x00: Trade (Witch) is now level 5\x00\n"
        ": болтовня в чате про is now level без скобок\n"
    )
    events = clientlog.parse_level_events(text)
    assert [e.level for e in events] == [5]


def test_parse_rejects_out_of_range_level():
    line = ": Exile (Witch) is now level 999"
    assert clientlog.parse_level_events(line) == []


def test_current_session_tail():
    text = "old session\n***** LOG FILE OPENING *****\nnew session"
    assert clientlog.current_session_tail(text).startswith("***** LOG FILE OPENING")
    assert clientlog.current_session_tail("no marker here") == "no marker here"


def test_split_complete_lines():
    complete, pending = clientlog.split_complete_lines("par", "tial\nfull line\nrest")
    assert complete == "partial\nfull line\n"
    assert pending == "rest"
    complete, pending = clientlog.split_complete_lines("", "no newline")
    assert complete == ""
    assert pending == "no newline"


def test_class_matches_ru_alias():
    assert clientlog.class_matches("Witch", "Necromancer", "Ведьма")
    assert clientlog.class_matches("Witch", "Necromancer", "некромант")
    assert not clientlog.class_matches("Witch", "Necromancer", "Дикарь")
    assert not clientlog.class_matches("Witch", "Necromancer", "")
