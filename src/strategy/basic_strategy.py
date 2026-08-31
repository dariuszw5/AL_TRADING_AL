class BasicStrategy:
    def generate_signal(
        self,
        sma_value,
        ema_value,
        rsi_value,
        min_difference=0.0,
        buy_rsi=30.0,
        sell_rsi=70.0,
        previous_ema=None
    ):
        difference = abs(ema_value - sma_value)

        if difference < min_difference:
            return "HOLD"

        if ema_value > sma_value and rsi_value < buy_rsi:
            return "BUY"

        if ema_value < sma_value and rsi_value > sell_rsi:
            return "SELL"

        return "HOLD"
