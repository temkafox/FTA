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


def test_gem_drop_row_maps_point_to_insert_position(app):
    from PyQt5.QtCore import QPoint

    from actpilot.editor import GemList

    widget = GemList()
    widget.addItems(["Камень 1", "Камень 2", "Камень 3"])
    widget.resize(220, 300)
    first = widget.visualItemRect(widget.item(0))
    assert widget._drop_row(FakeDropEvent(first.center())) == 0
    assert widget._drop_row(FakeDropEvent(QPoint(10, 290))) == 3


def test_tree_insert_position():
    from actpilot.editor import GemStageTree

    assert GemStageTree.insert_position(1, False) == 1
    assert GemStageTree.insert_position(1, True) == 2
    assert GemStageTree.insert_position(-1, False) == -1


def test_gem_tab_drag_surface_is_the_visible_tree(editor):
    """Связки живут в дереве: список связок спрятан, перетаскивать нужно дерево."""
    editor.tabs.setCurrentIndex(1)
    editor.show()

    assert editor.link_list.isHidden()
    tree = editor.gem_stage_tree
    assert tree.isVisible()
    assert tree.dragEnabled() and tree.acceptDrops()
    assert editor.gem_list.isVisible()
    assert editor.gem_list.dragEnabled() and editor.gem_list.acceptDrops()


def tree_texts(editor):
    tree = editor.gem_stage_tree
    header = tree.topLevelItem(0)
    return [header.child(row).text(0) for row in range(header.childCount())]


def test_tree_shows_reordered_links(editor):
    assert tree_texts(editor) == ["Freezing Pulse — Arcane Surge", "Frostbolt"]

    editor._links_reordered(1, 0)

    assert tree_texts(editor) == ["Frostbolt", "Freezing Pulse — Arcane Surge"]


def test_tree_shows_moved_gem(editor):
    editor.gem_stage_tree.setCurrentItem(
        editor.gem_stage_tree.topLevelItem(0).child(0)
    )
    editor._gem_dropped(1, 1)

    assert tree_texts(editor) == ["Freezing Pulse", "Frostbolt — Arcane Surge"]


def test_tree_headers_are_not_draggable(editor):
    from PyQt5.QtCore import Qt

    header = editor.gem_stage_tree.topLevelItem(0)
    assert not header.flags() & Qt.ItemIsDragEnabled
    assert header.child(0).flags() & Qt.ItemIsDragEnabled


class FakeTreeDrop:
    """Событие drop: настоящее подделать нельзя — у него не задать source()."""

    def __init__(self, source, point):
        self._source = source
        self._point = point
        self.action = None
        self.ignored = False

    def source(self):
        return self._source

    def pos(self):
        return self._point

    def setDropAction(self, action):
        self.action = action

    def accept(self):
        pass

    def ignore(self):
        self.ignored = True


def shown_tree(editor):
    editor.tabs.setCurrentIndex(1)
    editor.show()
    return editor.gem_stage_tree


def center_of(tree, item):
    return tree.visualItemRect(item).center()


def test_drop_of_link_onto_another_link_reorders(editor):
    from PyQt5.QtCore import Qt

    tree = shown_tree(editor)
    header = tree.topLevelItem(0)
    tree.setCurrentItem(header.child(0))
    moves = []
    tree.link_moved.connect(lambda source, target: moves.append((source, target)))

    event = FakeTreeDrop(tree, center_of(tree, header.child(1)))
    tree.dropEvent(event)

    assert moves == [(0, 1)]
    assert event.action == Qt.IgnoreAction


def test_drop_of_link_onto_stage_header_is_rejected(editor):
    tree = shown_tree(editor)
    header = tree.topLevelItem(0)
    tree.setCurrentItem(header.child(0))
    refusals = []
    tree.rejected.connect(refusals.append)

    tree.dropEvent(FakeTreeDrop(tree, center_of(tree, header)))

    assert refusals == [tree.OTHER_STAGE_LINK]


def test_drop_of_gem_onto_link_moves_it(editor):
    tree = shown_tree(editor)
    header = tree.topLevelItem(0)
    tree.setCurrentItem(header.child(0))
    editor.gem_list.setCurrentRow(1)
    drops = []
    tree.gem_dropped.connect(lambda gem, link: drops.append((gem, link)))

    tree.dropEvent(FakeTreeDrop(editor.gem_list, center_of(tree, header.child(1))))

    assert drops == [(1, 1)]


def test_drop_from_foreign_widget_is_ignored(editor):
    tree = shown_tree(editor)
    header = tree.topLevelItem(0)
    tree.setCurrentItem(header.child(0))

    event = FakeTreeDrop(editor.link_list, center_of(tree, header.child(1)))
    tree.dropEvent(event)

    assert event.ignored


def test_tree_copies_and_pastes_link_by_hotkeys(editor):
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QKeyEvent

    tree = editor.gem_stage_tree
    tree.setCurrentItem(tree.topLevelItem(0).child(1))
    tree.keyPressEvent(QKeyEvent(QKeyEvent.KeyPress, Qt.Key_C, Qt.ControlModifier))
    assert QApplication.clipboard().text() == "Frostbolt"

    tree.keyPressEvent(QKeyEvent(QKeyEvent.KeyPress, Qt.Key_V, Qt.ControlModifier))
    assert tree_texts(editor) == [
        "Freezing Pulse — Arcane Surge", "Frostbolt", "Frostbolt",
    ]


def test_paste_without_copy_reports(editor):
    type(editor)._link_buffer = None
    editor._paste_link()
    assert editor.message.text() == "Сначала скопируйте связку"
