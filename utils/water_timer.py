"""
utils/water_timer.py
喝水提醒倒數邏輯（純邏輯，不依賴 Qt，方便測試）
"""


class WaterCountdown:
    """以「秒」為單位的倒數器。tick() 到期回傳 True 並自動重設為完整間隔。"""

    def __init__(self, interval_minutes, enabled=True):
        self._interval_minutes = max(1, int(interval_minutes))
        self._enabled = bool(enabled)
        self.remaining = self._interval_minutes * 60

    @property
    def interval_minutes(self):
        return self._interval_minutes

    @property
    def enabled(self):
        return self._enabled

    def tick(self, seconds=1):
        """倒數 seconds 秒；停用時不倒數並回傳 False；到期回傳 True 並重設。"""
        if not self._enabled:
            return False
        self.remaining -= seconds
        if self.remaining <= 0:
            self.reset()
            return True
        return False

    def snooze(self, minutes=10):
        """延後：把剩餘時間改成 minutes 分鐘。"""
        self.remaining = max(1, int(minutes)) * 60

    def reset(self):
        self.remaining = self._interval_minutes * 60

    def set_interval(self, minutes):
        self._interval_minutes = max(1, int(minutes))
        self.reset()

    def set_enabled(self, enabled):
        """啟用時重設倒數；停用時保留剩餘值但不再倒數。"""
        enabled = bool(enabled)
        if enabled and not self._enabled:
            self.reset()
        self._enabled = enabled
