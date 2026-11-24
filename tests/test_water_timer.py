from utils.water_timer import WaterCountdown


def test_initial_remaining():
    c = WaterCountdown(2)
    assert c.remaining == 120
    assert c.enabled is True


def test_tick_counts_down_without_firing():
    c = WaterCountdown(1)
    assert c.tick() is False
    assert c.remaining == 59


def test_tick_fires_and_resets_on_expire():
    c = WaterCountdown(1)
    assert c.tick(59) is False
    assert c.tick() is True
    assert c.remaining == 60


def test_tick_overshoot_fires_and_resets():
    c = WaterCountdown(1)
    assert c.tick(100) is True
    assert c.remaining == 60


def test_snooze_default_ten_minutes():
    c = WaterCountdown(30)
    c.snooze()
    assert c.remaining == 600
    c.snooze(5)
    assert c.remaining == 300


def test_reset_restores_full_interval():
    c = WaterCountdown(3)
    c.tick(50)
    c.reset()
    assert c.remaining == 180


def test_set_interval_resets():
    c = WaterCountdown(3)
    c.tick(50)
    c.set_interval(5)
    assert c.interval_minutes == 5
    assert c.remaining == 300


def test_disabled_tick_does_not_count_or_fire():
    c = WaterCountdown(1, enabled=False)
    assert c.tick() is False
    assert c.remaining == 60


def test_set_enabled_true_resets_countdown():
    c = WaterCountdown(1, enabled=False)
    c.remaining = 5
    c.set_enabled(True)
    assert c.enabled is True
    assert c.remaining == 60
    c.set_enabled(False)
    assert c.enabled is False
