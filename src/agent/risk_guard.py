class RiskGuard:

    def __init__(self, max_daily_loss=100.0):
        self.max_daily_loss = float(max_daily_loss)
        self.daily_loss = 0.0
        self.current_day = None

    def _get_day(self, timestamp):
        if timestamp is None:
            return None

        timestamp = int(timestamp)

        if timestamp > 10_000_000_000:
            timestamp = timestamp // 1000

        import datetime

        return datetime.datetime.fromtimestamp(
            timestamp,
            tz=datetime.timezone.utc
        ).date()

    def _update_day(self, timestamp=None):
        if timestamp is None:
            return

        day = self._get_day(timestamp)

        if day is None:
            return

        if self.current_day is None:
            self.current_day = day
            return

        if day != self.current_day:
            self.current_day = day
            self.daily_loss = 0.0

    def can_trade(self, timestamp=None):
        self._update_day(timestamp)

        return self.daily_loss < self.max_daily_loss

    def record_loss(self, amount, timestamp=None):
        self._update_day(timestamp)

        if amount > 0:
            self.daily_loss += float(amount)

    def record_profit(self, amount, timestamp=None):
        self._update_day(timestamp)

        if amount > 0:
            return

    def reset(self):
        self.daily_loss = 0.0
        self.current_day = None