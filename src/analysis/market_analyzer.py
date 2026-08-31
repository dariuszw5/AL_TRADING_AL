from src.data.data_provider import DataProvider
from src.analysis.indicators import sma, ema, rsi, rsi_wilder


class MarketAnalyzer:
    def __init__(self, rsi_method="classic"):
        if rsi_method not in ("classic", "wilder"):
            raise ValueError(
                "rsi_method must be 'classic' or 'wilder'"
            )

        self.provider = DataProvider()
        self.rsi_method = rsi_method

    def analyze(self, candles=None):
        if candles is None:
            candles = self.provider.get_candles(
                symbol="BTCUSDT",
                interval="1m",
                limit=100
            )

        closes = [candle.close for candle in candles]

        if self.rsi_method == "wilder":
            rsi_values = rsi_wilder(closes, 14)
        else:
            rsi_values = rsi(closes, 14)

        return {
            "sma": sma(closes, 20),
            "ema": ema(closes, 20),
            "rsi": rsi_values
        }