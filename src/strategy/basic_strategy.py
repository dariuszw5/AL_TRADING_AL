class BasicStrategy:
    def generate_signal(self, sma_value, ema_value, rsi_value):
        if ema_value > sma_value and rsi_value < 40:
            return "BUY"

        if ema_value < sma_value and rsi_value > 60:
            return "SELL"

        return "HOLD"