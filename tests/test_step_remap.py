import pytest

from PyQt5.QtWidgets import QApplication

from actpilot.steps import normalize_steps
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


def make_content(qapp, data, timer=None):
    content = ContentArea()
    if timer is not None:
        content.set_timer(timer)
    content.load(data)
    return content


def norm(data):
    return normalize_steps(data)[0]


def test_insert_step_keeps_progress_by_text(qapp):
    timer = FakeTimer(60)
    src = make_content(qapp, {"Act 1": ["a", "b", "c"]}, timer)
    src._on_click(src.all_steps[2])  # выполнить a, b, c
    state = src.get_state()

    dst = make_content(qapp, {"Act 1": ["a", "x", "b", "c"]})  # вставили x между a и b
    dst.set_state(state)
    done = {s.text: s.done for s in dst.all_steps}
    assert done == {"a": True, "x": False, "b": True, "c": True}
    assert dst.all_steps[0].split == "01:00"  # отсечка a сохранилась


def test_delete_completed_step_remaps_rest(qapp):
    timer = FakeTimer(30)
    src = make_content(qapp, {"Act 1": ["a", "b", "c"]}, timer)
    src._on_click(src.all_steps[2])
    state = src.get_state()

    dst = make_content(qapp, {"Act 1": ["a", "c"]})  # удалили b
    dst.set_state(state)
    assert [s.done for s in dst.all_steps] == [True, True]
    assert [s.text for s in dst.all_steps] == ["a", "c"]


def test_duplicate_texts_map_in_order(qapp):
    timer = FakeTimer(60)
    src = make_content(qapp, {"Act 1": ["тп", "b", "тп", "d"]}, timer)
    src._on_click(src.all_steps[1])  # выполнить первый "тп" и "b"
    state = src.get_state()

    dst = make_content(qapp, {"Act 1": ["тп", "b", "тп", "d"]})
    dst.set_state(state)
    # первый "тп" и "b" done, второй "тп" и "d" — нет
    assert [s.done for s in dst.all_steps] == [True, True, False, False]


def test_missing_step_texts_uses_index_fallback(qapp):
    src = make_content(qapp, {"Act 1": ["a", "b", "c"]})
    src._on_click(src.all_steps[1])
    state = src.get_state()
    for group_state in state.values():
        group_state.pop("step_texts", None)  # старый формат без текстов

    dst = make_content(qapp, {"Act 1": ["a", "b", "c"]})
    dst.set_state(state)
    assert [s.done for s in dst.all_steps] == [True, True, False]


def test_renamed_act_drops_its_progress(qapp):
    src = make_content(qapp, {"Act 1": ["a", "b"], "Act 2": ["c", "d"]})
    src._on_click(src.all_steps[3])  # выполнить всё
    state = src.get_state()

    # переименовали Act 1 -> Пролог, Act 2 не тронут
    dst = make_content(qapp, {"Пролог": ["a", "b"], "Act 2": ["c", "d"]})
    dst.set_state(state)
    done = {s.text: s.done for s in dst.all_steps}
    assert done["a"] is False and done["b"] is False  # прогресс акта сброшен
    assert done["c"] is True and done["d"] is True     # соседний акт цел


def test_round_trip_unchanged_steps_identical(qapp):
    timer = FakeTimer(90)
    src = make_content(qapp, {"Act 1": ["a", "b", "c"], "Act 2": ["d"]}, timer)
    src._on_click(src.all_steps[1])
    state = src.get_state()

    dst = make_content(qapp, {"Act 1": ["a", "b", "c"], "Act 2": ["d"]})
    dst.set_state(state)
    assert [s.done for s in dst.all_steps] == [s.done for s in src.all_steps]
    assert [s.split for s in dst.all_steps] == [s.split for s in src.all_steps]


def test_act_time_restored_only_when_complete(qapp):
    timer = FakeTimer(120)
    src = make_content(qapp, {"Act 1": ["a", "b"]}, timer)
    src._on_click(src.all_steps[1])  # акт полностью пройден -> есть время
    state = src.get_state()
    assert state["Act 1"]["time"] is not None

    # добавили шаг c: акт больше не завершён, время акта не показываем
    dst = make_content(qapp, {"Act 1": ["a", "b", "c"]})
    dst.set_state(state)
    assert dst.groups[0]._completion_time is None
    assert [s.done for s in dst.all_steps] == [True, True, False]


# --- матчинг по стабильному id (переименование не ломает прогресс) ---

def test_rename_step_keeps_progress_by_id(qapp):
    steps = norm({"Act 1": ["Убиваем хиллока", "Идём в побережье", "Босс"]})
    timer = FakeTimer(60)
    src = make_content(qapp, steps, timer)
    src._on_click(src.all_steps[2])  # всё done со сплитами
    state = src.get_state()

    # переименовали второй шаг, id тот же
    renamed = {"Act 1": [dict(s) for s in steps["Act 1"]]}
    renamed["Act 1"][1]["text"] = "Идём в ПОБЕРЕЖЬЕ (впка)"
    dst = make_content(qapp, renamed)
    dst.set_state(state)

    done = {s.text: s.done for s in dst.all_steps}
    assert done == {"Убиваем хиллока": True, "Идём в ПОБЕРЕЖЬЕ (впка)": True, "Босс": True}
    assert dst.all_steps[1].split is not None  # отсечка поехала за id, не за текстом


def test_reorder_steps_keeps_progress_by_id(qapp):
    steps = norm({"Act 1": ["a", "b", "c"]})
    src = make_content(qapp, steps)
    src._on_click(src.all_steps[1])  # a, b done
    state = src.get_state()

    order = steps["Act 1"]
    reordered = {"Act 1": [order[2], order[0], order[1]]}  # c, a, b
    dst = make_content(qapp, reordered)
    dst.set_state(state)
    done = {s.text: s.done for s in dst.all_steps}
    assert done == {"a": True, "b": True, "c": False}


def test_rename_plus_insert_plus_delete(qapp):
    steps = norm({"Act 1": ["a", "b", "c", "d"]})
    src = make_content(qapp, steps)
    src._on_click(src.all_steps[2])  # a, b, c done; d нет
    state = src.get_state()

    a, b, c, d = steps["Act 1"]
    b = dict(b, text="b переименован")           # переименовали b (id тот же)
    new = {"id": "new0", "text": "новый"}          # вставили новый
    changed = {"Act 1": [a, new, b, d]}            # удалили c, порядок изменён
    dst = make_content(qapp, changed)
    dst.set_state(state)
    done = {s.text: s.done for s in dst.all_steps}
    assert done == {"a": True, "новый": False, "b переименован": True, "d": False}


def test_id_mismatch_falls_back_to_text(qapp):
    src = make_content(qapp, norm({"Act 1": ["a", "b", "c"]}))
    src._on_click(src.all_steps[1])  # a, b done
    state = src.get_state()

    # свежие id (другой uuid), тексты те же — id не совпадут, работает текстовый фолбэк
    dst = make_content(qapp, norm({"Act 1": ["a", "b", "c"]}))
    dst.set_state(state)
    assert [s.done for s in dst.all_steps] == [True, True, False]
