from src.analysis.market_analyzer import MarketAnalyzer
from src.strategy.basic_strategy import BasicStrategy


class StrategyEngine:
    def __init__(self):
        self.analyzer = MarketAnalyzer()
        self.strategy = BasicStrategy()

    def run(self):
        analysis = self.analyzer.analyze()

        sma_values = analysis["sma"]
        ema_values = analysis["ema"]
        rsi_values = analysis["rsi"]

        if not sma_values or not ema_values or not rsi_values:
            return "HOLD"

        sma_value = sma_values[-1]
        ema_value = ema_values[-1]
        rsi_value = rsi_values[-1]

        return self.strategy.generate_signal(
            sma_value=sma_value,
            ema_value=ema_value,
            rsi_value=rsi_value
        )