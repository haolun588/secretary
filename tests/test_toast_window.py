import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PyQt6.QtWidgets")
from PyQt6.QtCore import QAbstractAnimation  # noqa: E402

from ui import theme  # noqa: E402
from ui.styles import app_stylesheet  # noqa: E402
from ui.toast_window import ACTION_MIN_DISPLAY_MS, RESUME_DELAY_MS, ToastStack, ToastWindow  # noqa: E402


@pytest.fixture(autouse=True)
def _styled(_session_qapplication, monkeypatch):
    monkeypatch.setattr(ToastWindow, "play_notification_sound", lambda self: None)
    _session_qapplication.setStyleSheet(app_stylesheet())
    yield
    _session_qapplication.setStyleSheet("")


def _make(**kw):
    kw.setdefault("title", "標題")
    kw.setdefault("message", "訊息")
    return ToastWindow(**kw)


def test_width_fixed_and_height_adapts_to_message():
    short = _make()
    long = _make(message="很長的訊息" * 40)
    assert short.width() == long.width() == theme.TOAST_WIDTH
    assert long.height() > short.height()
    short.deleteLater()
    long.deleteLater()


def test_kind_sets_bar_property_and_fallback():
    for kind in ("info", "water", "danger"):
        t = _make(kind=kind)
        assert t.bar.property("kind") == kind
        t.deleteLater()
    t = _make(kind="bogus")
    assert t.kind == "info"
    t.deleteLater()


def test_no_actions_uses_given_display_time():
    t = _make(display_time_ms=3000)
    assert t.action_buttons == []
    assert t._hide_timer.isActive()
    assert t._hide_timer.interval() == 3000
    t.deleteLater()


def test_actions_enforce_minimum_display_time():
    t = _make(display_time_ms=3000, actions=[("甲", lambda: None)])
    assert t.display_time_ms == ACTION_MIN_DISPLAY_MS
    assert t._hide_timer.interval() == ACTION_MIN_DISPLAY_MS
    assert [b.text() for b in t.action_buttons] == ["甲"]
    t.deleteLater()


def test_action_click_calls_callback_and_closes():
    called = []
    t = _make(actions=[("甲", lambda: called.append("a")), ("乙", lambda: called.append("b"))])
    closed = []
    t.close = lambda: closed.append(True)  # 避免真的關閉視窗
    t.action_buttons[1].click()
    assert called == ["b"]
    assert closed == [True]
    assert not t._hide_timer.isActive()
    t.deleteLater()


def test_action_callback_exception_does_not_break_close():
    def boom():
        raise RuntimeError("x")

    t = _make(actions=[("甲", boom)])
    closed = []
    t.close = lambda: closed.append(True)
    t.action_buttons[0].click()
    assert closed == [True]
    t.deleteLater()


def test_close_button_closes():
    t = _make()
    closed = []
    t.close = lambda: closed.append(True)
    t.close_btn.click()
    assert closed == [True]
    t.deleteLater()


def test_pause_stops_timer_and_animation_and_restores_opacity():
    t = _make(fade_time_ms=5000)
    t.start_fade_out()
    assert t.anim.state() == QAbstractAnimation.State.Running
    t.opacity_effect.setOpacity(0.4)
    t.pause()
    assert not t._hide_timer.isActive()
    assert t.anim.state() == QAbstractAnimation.State.Stopped
    assert t.opacity_effect.opacity() == 1.0
    t.deleteLater()


def test_resume_restarts_timer_with_short_delay():
    t = _make()
    t.pause()
    t.resume()
    assert t._hide_timer.isActive()
    assert t._hide_timer.interval() == RESUME_DELAY_MS
    t.deleteLater()


def test_enter_leave_events_pause_and_resume():
    from PyQt6.QtCore import QEvent, QPointF
    from PyQt6.QtGui import QEnterEvent
    t = _make()
    t.enterEvent(QEnterEvent(QPointF(1, 1), QPointF(1, 1), QPointF(1, 1)))
    assert not t._hide_timer.isActive()
    t.leaveEvent(QEvent(QEvent.Type.Leave))
    assert t._hide_timer.isActive()
    t.deleteLater()


def test_start_fade_out_ignored_while_paused():
    t = _make()
    t.pause()
    t.start_fade_out()
    assert t.anim is None
    t.deleteLater()


def test_position_stack_offset_moves_up():
    t = _make()
    t.position_at_bottom_right()
    y0 = t.y()
    t.position_at_bottom_right(stack_offset=100)
    assert t.y() == y0 - 100
    t.deleteLater()


def test_resume_with_actions_keeps_remaining_display_time():
    t = _make(actions=[("甲", lambda: None)])
    t.pause()
    t.resume()
    assert t._hide_timer.interval() > RESUME_DELAY_MS
    assert t._hide_timer.interval() <= ACTION_MIN_DISPLAY_MS
    t.deleteLater()


def test_resume_without_actions_stays_short_delay():
    t = _make(display_time_ms=9000)
    t.pause()
    t.resume()
    assert t._hide_timer.interval() == RESUME_DELAY_MS
    t.deleteLater()


def test_toast_stack_restacks_after_removal():
    stack = ToastStack()
    a, b = _make(), _make()
    stack.add(a)
    stack.add(b)
    base = _make()
    base.position_at_bottom_right()
    bottom_y = base.y()
    assert b.y() == bottom_y - (a.height() + stack.gap)  # B 疊在 A 上方
    a.close = lambda: None
    stack.remove(a)
    assert b.y() == bottom_y  # B 重新回到底部
    c = _make()
    stack.add(c)
    assert c.y() + c.height() + stack.gap == b.y()  # C 在 B 上方，不重疊
    assert stack.toasts == [b, c]
    for t in (a, b, c, base):
        t.deleteLater()


def test_toast_stack_survives_dead_toast():
    stack = ToastStack()
    a = _make()
    stack.add(a)

    def boom(offset=0):
        raise RuntimeError("deleted")

    a.position_at_bottom_right = boom
    stack.restack()
    assert stack.toasts == []
    a.deleteLater()
