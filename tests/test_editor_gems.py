import pytest
from PyQt5.QtWidgets import QApplication, QWidget

from actpilot.editor import ManualBuildEditor


def gem(name, support=False):
    return {"name": name, "support": support, "level": "20", "quality": "0"}


def build():
    return {
        "format": "pob1",
        "class": "Witch",
        "ascendancy": "Necromancer",
        "trees": [{"level": 1, "title": "Level 1", "nodes": [], "masteries": ""}],
        "gem_sets": [
            {
                "level": 1,
                "title": "Start",
                "links": [
                    {"label": "A", "gems": [gem("Freezing Pulse"), gem("Arcane Surge", True)]},
                    {"label": "B", "gems": [gem("Frostbolt")]},
                ],
            }
        ],
    }


class StubOverlay:
    def __init__(self):
        self.profile = {"id": "x", "name": "Тест", "level": 1, "build": build()}
        self.saved = 0

    def active_profile(self):
        return self.profile

    def save_profiles(self):
        self.saved += 1


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def editor(app):
    holder = QWidget()
    dialog = ManualBuildEditor(StubOverlay(), parent=holder)
    dialog.gem_level_picker.setValue(1)
    dialog.link_list.setCurrentRow(0)
    yield dialog
    dialog.deleteLater()


def links(editor, level=None):
    stages = editor.state["gem_stages"]
    if level is None:
        return stages[editor._active_stage_index]["links"]
    return next(stage for stage in stages if stage["level"] == level)["links"]


def names(link):
    return [item["name"] for item in link["gems"]]


def test_reorder_gems_inside_link(editor):
    editor._gems_reordered(0, 2)
    assert names(links(editor)[0]) == ["Arcane Surge", "Freezing Pulse"]


def test_move_gem_to_another_link(editor):
    editor._gem_dropped(1, 1)
    assert names(links(editor)[0]) == ["Freezing Pulse"]
    assert names(links(editor)[1]) == ["Frostbolt", "Arcane Surge"]


def test_reorder_links(editor):
    editor._links_reordered(1, 0)
    assert [link["label"] for link in links(editor)] == ["B", "A"]


def test_duplicate_link(editor):
    editor._duplicate_link()
    assert len(links(editor)) == 3
    assert names(links(editor)[1]) == ["Freezing Pulse", "Arcane Surge"]


def test_edit_on_higher_level_keeps_earlier_stage(editor):
    editor.gem_level_picker.setValue(40)
    editor.link_list.setCurrentRow(0)
    editor._gems_reordered(0, 2)

    levels = [stage["level"] for stage in editor.state["gem_stages"]]
    assert levels == [1, 40]
    assert names(links(editor, 1)[0]) == ["Freezing Pulse", "Arcane Surge"]
    assert names(links(editor, 40)[0]) == ["Arcane Surge", "Freezing Pulse"]


def test_copy_link_and_paste_on_another_level(editor):
    editor.link_list.setCurrentRow(1)
    editor._copy_link()
    assert QApplication.clipboard().text() == "Frostbolt"

    editor.gem_level_picker.setValue(60)
    editor._paste_link()

    pasted = links(editor, 60)
    assert [names(link) for link in pasted] == [
        ["Freezing Pulse", "Arcane Surge"], ["Frostbolt"], ["Frostbolt"],
    ]
    assert len(links(editor, 1)) == 2


def test_gem_type_comes_from_name(editor):
    assert not hasattr(editor, "support_check")

    editor.gem_combo.setCurrentText("Added Fire Damage")
    editor._add_gem()
    added = links(editor)[0]["gems"][-1]
    assert (added["name"], added["support"]) == ("Added Fire Damage", True)

    editor.gem_combo.setCurrentText("Frostbolt")
    editor._add_gem()
    assert links(editor)[0]["gems"][-1]["support"] is False


class FakeDropEvent:
    def __init__(self, point):
        self._point = point

    def pos(self):
        return self._point


def test_drop_row_maps_point_to_insert_position(app):
    from PyQt5.QtCore import QPoint

    from actpilot.editor import LinkList

    widget = LinkList()
    widget.addItems(["Связка 1", "Связка 2", "Связка 3"])
    widget.resize(220, 300)
    first = widget.visualItemRect(widget.item(0))
    assert widget._drop_row(FakeDropEvent(first.center())) == 0
    assert widget._drop_row(FakeDropEvent(QPoint(10, 290))) == 3


def test_paste_without_copy_reports(editor):
    type(editor)._link_buffer = None
    editor._paste_link()
    assert editor.message.text() == "Сначала скопируйте связку"
