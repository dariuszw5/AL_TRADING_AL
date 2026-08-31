import time
import json
import requests

from src.data.candle import Candle


class DataProvider:
    BASE_URL = "https://data-api.binance.vision"

    def __init__(self):
        self.data = []

    def _get(self, endpoint, params):
        last_error = None

        for attempt in range(3):
            try:
                response = requests.get(
                    f"{self.BASE_URL}{endpoint}",
                    params=params,
                    timeout=30
                )

                response.raise_for_status()
                return response

            except requests.exceptions.RequestException as error:
                last_error = error

                if attempt < 2:
                    time.sleep(1)

        raise last_error

    def _convert_candles(self, raw_data):
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

        return candles

    def save_candles(self, candles, file_path):
        data = []

        for candle in candles:
            data.append({
                "timestamp": candle.timestamp,
                "open": candle.open,
                "high": candle.high,
                "low": candle.low,
                "close": candle.close,
                "volume": candle.volume
            })

        with open(
            file_path,
            "w",
            encoding="utf-8"
        ) as file:
            json.dump(
                data,
                file,
                indent=2
            )

    def load_candles(self, file_path):
        with open(
            file_path,
            "r",
            encoding="utf-8"
        ) as file:
            data = json.load(file)

        candles = []

        for item in data:
            candles.append(
                Candle(
                    timestamp=item["timestamp"],
                    open=float(item["open"]),
                    high=float(item["high"]),
                    low=float(item["low"]),
                    close=float(item["close"]),
                    volume=float(item["volume"])
                )
            )

        self.data = candles

        return candles

    def get_candles(
        self,
        symbol="BTCUSDT",
        interval="1m",
        limit=100
    ):
        response = self._get(
            "/api/v3/klines",
            {
                "symbol": symbol,
                "interval": interval,
                "limit": limit
            }
        )

        raw_data = response.json()

        candles = self._convert_candles(raw_data)

        self.data = candles

        return candles

    def get_historical_candles(
        self,
        symbol="BTCUSDT",
        interval="1m",
        limit=1000
    ):
        candles = []
        remaining = limit
        end_time = None

        while remaining > 0:
            batch_limit = min(1000, remaining)

            params = {
                "symbol": symbol,
                "interval": interval,
                "limit": batch_limit
            }

            if end_time is not None:
                params["endTime"] = end_time

            response = self._get(
                "/api/v3/klines",
                params
            )

            raw_data = response.json()

            if not raw_data:
                break

            batch = self._convert_candles(raw_data)

            candles = batch + candles
            remaining -= len(batch)

            end_time = raw_data[0][0] - 1

            if len(batch) < batch_limit:
                break

        self.data = candles

        return candles