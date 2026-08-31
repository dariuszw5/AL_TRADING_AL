class TradeHistory:
    def __init__(self):
        self.trades = []

    def add_trade(self, trade):
        self.trades.append(trade)

    def get_trades(self):
        return self.trades

    def count(self):
        return len(self.trades)