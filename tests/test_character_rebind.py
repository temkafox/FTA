import pytest
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QApplication, QWidget

from actpilot.build_dialog import CharacterRebindBuildDialog


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


class Content(QObject):
    active_step_changed = pyqtSignal()

    def get_active_step_info(self):
        return "Act 1", 0, ""


class StubOverlay(QWidget):
    def __init__(self, profile, client_path):
        super().__init__()
        self.settings = {"poe1_client_path": str(client_path)}
        self.content = Content()
        self.profile_data = {"active_profile_id": "p", "profiles": [dict(profile, id="p")]}
        self.saved = 0

    def active_profile(self):
        return self.profile_data["profiles"][0]

    def save_profiles(self):
        self.saved += 1

    def switch_profile(self, _):
        pass

    def create_profile(self, _):
        pass


def make_dialog(tmp_path, **profile):
    base = {"name": "ййй", "game": "poe1", "level": 53, "campaign": {}, "build": {"class": "Witch", "gem_sets": []}}
    overlay = StubOverlay({**base, **profile}, tmp_path / "missing-Client.txt")
    return overlay, CharacterRebindBuildDialog(overlay)


def test_foreign_character_offers_rebind_without_touching_level(qapp, tmp_path):
    overlay, dialog = make_dialog(tmp_path, log_character_name="Old")
    dialog._on_level_seen("New", "Witch", 6)
    profile = overlay.active_profile()
    assert (profile["log_character_name"], profile["level"]) == ("Old", 53)
    assert not dialog.rebind_button.isHidden()
    assert "New" in dialog.rebind_button.text() and "Old" in dialog.log_status.text()


def test_rebind_button_switches_character_and_level(qapp, tmp_path):
    overlay, dialog = make_dialog(tmp_path, log_character_name="Old")
    dialog._on_level_seen("New", "Witch", 6)
    dialog.rebind_button.click()
    profile = overlay.active_profile()
    assert (profile["log_character_name"], profile["level"]) == ("New", 6)
    assert dialog.rebind_button.isHidden()
    dialog._on_level_seen("New", "Witch", 7)
    assert profile["level"] == 7


def test_unbound_profile_with_other_class_also_offers_rebind(qapp, tmp_path):
    overlay, dialog = make_dialog(tmp_path, build={"class": "Duelist", "gem_sets": []})
    dialog._on_level_seen("Иона", "Witch", 3)
    assert "класс не совпадает" in dialog.log_status.text()
    assert not dialog.rebind_button.isHidden()


def test_own_character_keeps_prompt_hidden(qapp, tmp_path):
    overlay, dialog = make_dialog(tmp_path, log_character_name="Old")
    dialog._on_level_seen("Old", "Witch", 54)
    assert overlay.active_profile()["level"] == 54
    assert dialog.rebind_button.isHidden()
