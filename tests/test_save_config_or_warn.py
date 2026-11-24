from utils.config_manager import save_config_or_warn


def test_success_does_not_notify():
    notes = []
    assert save_config_or_warn({"a": 1}, lambda c: True, lambda t, m: notes.append((t, m))) is True
    assert notes == []


def test_false_result_notifies_danger_message():
    notes = []
    assert save_config_or_warn({}, lambda c: False, lambda t, m: notes.append((t, m))) is False
    assert len(notes) == 1 and notes[0][0] == "設定儲存失敗"


def test_exception_notifies():
    notes = []

    def boom(c):
        raise OSError("disk")

    assert save_config_or_warn({}, boom, lambda t, m: notes.append((t, m))) is False
    assert len(notes) == 1


def test_passes_config_to_saver():
    seen = []
    save_config_or_warn({"k": 2}, lambda c: seen.append(c) or True, lambda t, m: None)
    assert seen == [{"k": 2}]
