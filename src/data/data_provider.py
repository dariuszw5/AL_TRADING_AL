import requests

from src.data.candle import Candle


class DataProvider:
    BASE_URL = "https://data-api.binance.vision"

    def __init__(self):
        self.data = []

    def get_candles(self, symbol="BTCUSDT", interval="1m", limit=100):
        response = requests.get(
            f"{self.BASE_URL}/api/v3/klines",
            params={
                "symbol": symbol,
                "interval": interval,
                "limit": limit
            },
            timeout=10
        )

        response.raise_for_status()

        raw_data = response.json()

        candles = []

        for item in raw_data:
            candle = Candle(
                timestamp=item[0],
                open=float(item[1]),
                high=float(item[2]),
                low=float(item[3]),
                close=float(item[4]),
                volume=float(item[5])
            )

            candles.append(candle)

        self.data = candles

        return candles