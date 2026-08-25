from src.data.data_provider import DataProvider
from src.analysis.indicators import sma, ema, rsi


class MarketAnalyzer:
    def __init__(self):
        self.provider = DataProvider()

    def analyze(self):
        candles = self.provider.get_candles(
            symbol="BTCUSDT",
            interval="1m",
            limit=100
        )

        closes = [candle.close for candle in candles]

        return {
            "sma": sma(closes, 20),
            "ema": ema(closes, 20),
            "rsi": rsi(closes, 14)
        }