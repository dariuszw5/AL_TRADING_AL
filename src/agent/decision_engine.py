from src.strategy.strategy_engine import StrategyEngine


class DecisionEngine:
    def __init__(
        self,
        buy_rsi=30.0,
        sell_rsi=70.0,
        min_difference=1.0,
        rsi_method="classic"
    ):
        self.strategy_engine = StrategyEngine(
            buy_rsi=buy_rsi,
            sell_rsi=sell_rsi,
            min_difference=min_difference,
            rsi_method=rsi_method
        )

    def decide(self, analysis):
        if not analysis:
            return "HOLD"

        sma_values = analysis.get("sma", [])
        ema_values = analysis.get("ema", [])
        rsi_values = analysis.get("rsi", [])

        if not sma_values or not ema_values or not rsi_values:
            return "HOLD"

        sma_value = sma_values[-1]
        ema_value = ema_values[-1]
        rsi_value = rsi_values[-1]

        previous_ema = None

        if len(ema_values) >= 2:
            previous_ema = ema_values[-2]

        return self.strategy_engine.strategy.generate_signal(
            sma_value=sma_value,
            ema_value=ema_value,
            rsi_value=rsi_value,
            min_difference=self.strategy_engine.min_difference,
            buy_rsi=self.strategy_engine.buy_rsi,
            sell_rsi=self.strategy_engine.sell_rsi,
            previous_ema=previous_ema
        )