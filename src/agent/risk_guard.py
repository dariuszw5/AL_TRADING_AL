class RiskGuard:
    def __init__(self, max_daily_loss=100.0):
        self.max_daily_loss = float(max_daily_loss)
        self.daily_loss = 0.0

    def can_trade(self):
        return self.daily_loss < self.max_daily_loss

    def record_loss(self, amount):
        if amount > 0:
            self.daily_loss += float(amount)

    def record_profit(self, amount):
        if amount > 0:
            return

    def reset(self):
        self.daily_loss = 0.0