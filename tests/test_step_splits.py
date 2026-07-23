import pytest

from PyQt5.QtCore import QEvent, QPointF, Qt
from PyQt5.QtGui import QMouseEvent
from PyQt5.QtWidgets import QApplication

from actpilot.widgets import ContentArea


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


class FakeTimer:
    def __init__(self, elapsed=0):
        self.elapsed = elapsed

    def get_elapsed(self):
        return self.elapsed


def make_content(qapp, timer=None, data=None):
    content = ContentArea()
    if timer is not None:
        content.set_timer(timer)
    content.load(data or {"Act 1": ["a", "b", "c"], "Act 2": ["d"]})
    return content


def test_complete_current_stamps_split(qapp):
    timer = FakeTimer(83)
    content = make_content(qapp, timer)
    content.complete_current()
    assert content.all_steps[0].split == "01:23"
    assert not content.all_steps[0].split_label.isHidden()


def test_bulk_click_stamps_new_keeps_existing(qapp):
    timer = FakeTimer(60)
    content = make_content(qapp, timer)
    content.complete_current()  # step 0 at 01:00
    assert content.all_steps[0].split == "01:00"

    timer.elapsed = 300
    content._on_click(content.all_steps[2])  # bulk complete 1 and 2 at 05:00
    assert content.all_steps[0].split == "01:00"
    assert content.all_steps[1].split == "05:00"
    assert content.all_steps[2].split == "05:00"


def test_previous_current_clears_last_split(qapp):
    timer = FakeTimer(60)
    content = make_content(qapp, timer)
    content.complete_current()
    timer.elapsed = 120
    content.complete_current()
    assert content.all_steps[1].split == "02:00"

    content.previous_current()
    assert content.all_steps[1].split is None
    assert content.all_steps[1].split_label.isHidden()
    assert content.all_steps[0].split == "01:00"


def test_click_uncheck_clears_following_splits(qapp):
    timer = FakeTimer(300)
    content = make_content(qapp, timer)
    content._on_click(content.all_steps[2])  # complete 0,1,2
    assert all(content.all_steps[i].split == "05:00" for i in range(3))

    content._on_click(content.all_steps[1])  # uncheck 1 and following
    assert content.all_steps[0].split == "05:00"
    assert content.all_steps[1].split is None
    assert content.all_steps[2].split is None


def test_state_round_trip_restores_splits(qapp):
    timer = FakeTimer(90)
    content = make_content(qapp, timer)
    content.complete_current()
    state = content.get_state()
    assert state["Act 1"]["step_times"][0] == "01:30"

    fresh = make_content(qapp)
    fresh.set_state(state)
    assert fresh.all_steps[0].done
    assert fresh.all_steps[0].split == "01:30"
    assert not fresh.all_steps[0].split_label.isHidden()


def test_legacy_state_without_step_times(qapp):
    content = make_content(qapp)
    content.groups[0].set_state([True, False, False])  # legacy list form
    content.groups[1].set_state({"steps": [True], "time": None})  # dict without step_times
    assert content.all_steps[0].done
    assert content.all_steps[0].split is None
    assert content.all_steps[3].done
    assert content.all_steps[3].split is None


def test_reset_clears_all_splits(qapp):
    timer = FakeTimer(120)
    content = make_content(qapp, timer)
    content._on_click(content.all_steps[3])  # complete everything
    assert any(s.split for s in content.all_steps)

    content.reset()
    assert all(s.split is None for s in content.all_steps)
    assert all(s.split_label.isHidden() for s in content.all_steps)


def test_complete_without_timer(qapp):
    content = make_content(qapp)  # no timer set
    content.complete_current()
    assert content.all_steps[0].done
    assert content.all_steps[0].split is None


def test_splits_disabled_does_not_stamp(qapp):
    timer = FakeTimer(83)
    content = make_content(qapp, timer)
    content.set_show_splits(False)
    content.complete_current()
    assert content.all_steps[0].done
    assert content.all_steps[0].split is None
    assert content.all_steps[0].split_label.isHidden()


def test_toggle_hides_and_restores_splits(qapp):
    timer = FakeTimer(83)
    content = make_content(qapp, timer)
    content.complete_current()
    assert content.all_steps[0].split == "01:23"

    content.set_show_splits(False)
    assert content.all_steps[0].split == "01:23"  # данные сохранены
    assert content.all_steps[0].split_label.isHidden()

    content.set_show_splits(True)
    assert content.all_steps[0].split == "01:23"
    assert not content.all_steps[0].split_label.isHidden()


def test_step_completed_while_off_has_no_split(qapp):
    timer = FakeTimer(120)
    content = make_content(qapp, timer)
    content.set_show_splits(False)
    content.complete_current()  # шаг завершён с выключенной фичей
    content.set_show_splits(True)
    assert content.all_steps[0].done
    assert content.all_steps[0].split is None  # честный пропуск
    assert content.all_steps[0].split_label.isHidden()


def test_load_applies_show_splits_flag(qapp):
    content = make_content(qapp)
    content.set_show_splits(False)
    content.load({"Act 1": ["a", "b"]})  # свежие шаги
    assert all(not s._split_visible for s in content.all_steps)


def test_stage_duration_computed(qapp):
    timer = FakeTimer(60)
    content = make_content(qapp, timer)
    content.complete_current()  # step 0 → 01:00
    timer.elapsed = 150
    content.complete_current()  # step 1 → 02:30
    assert content.all_steps[0].duration == "01:00"  # 60 - 0
    assert content.all_steps[1].duration == "01:30"  # 150 - 60


def test_first_step_duration_equals_absolute(qapp):
    timer = FakeTimer(45)
    content = make_content(qapp, timer)
    content.complete_current()
    assert content.all_steps[0].duration == "00:45"


def test_toggle_switches_all_labels_globally(qapp):
    timer = FakeTimer(60)
    content = make_content(qapp, timer)
    content.complete_current()
    timer.elapsed = 150
    content.complete_current()
    # режим по умолчанию — общее время
    assert content.all_steps[0].split_label.text() == "01:00"
    assert content.all_steps[1].split_label.text() == "02:30"

    content._toggle_split_mode()
    assert content._split_mode == "stage"
    assert content.all_steps[0].split_label.text() == "01:00"  # длительность шага 0
    assert content.all_steps[1].split_label.text() == "01:30"  # длительность шага 1

    content._toggle_split_mode()
    assert content.all_steps[1].split_label.text() == "02:30"  # снова общее время


def test_split_click_toggles_mode_without_completing_step(qapp):
    timer = FakeTimer(60)
    content = make_content(qapp, timer)
    content.complete_current()  # step 0 done, у него есть отсечка
    step0 = content.all_steps[0]
    row_clicks = []
    step0.clicked.connect(lambda s: row_clicks.append(s))

    ev = QMouseEvent(QEvent.MouseButtonPress, QPointF(1, 1),
                     Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
    step0.split_label.mousePressEvent(ev)

    assert ev.isAccepted()
    assert content._split_mode == "stage"  # режим переключился глобально
    assert row_clicks == []                # завершение шага НЕ сработало
    assert step0.done is True              # состояние шага не тронуто


def test_rollback_clears_duration(qapp):
    timer = FakeTimer(60)
    content = make_content(qapp, timer)
    content.complete_current()
    timer.elapsed = 150
    content.complete_current()
    assert content.all_steps[1].duration == "01:30"

    content.previous_current()
    assert content.all_steps[1].duration is None
    assert content.all_steps[1].split is None
