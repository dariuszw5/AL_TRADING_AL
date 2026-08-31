class StrategyConfig:

    def __init__(
        self,
        buy_rsi=30.0,
        sell_rsi=70.0,
        min_difference=1.0,
        trading_fee=0.001,
        rsi_method="classic"
    ):
        self.buy_rsi = float(buy_rsi)
        self.sell_rsi = float(sell_rsi)
        self.min_difference = float(min_difference)
        self.trading_fee = float(trading_fee)
        self.rsi_method = rsi_method

    def to_dict(self):
        return {
            "buy_rsi": self.buy_rsi,
            "sell_rsi": self.sell_rsi,
            "min_difference": self.min_difference,
            "trading_fee": self.trading_fee,
            "rsi_method": self.rsi_method
        }