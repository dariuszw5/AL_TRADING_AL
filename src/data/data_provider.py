import time
import json
import requests

from src.data.candle import Candle
from src.data.assets import get_asset


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
                    timeout=10
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
        asset = get_asset(symbol)

        if asset.provider == "yahoo":
            candles = self._get_yahoo_candles(
                provider_symbol=asset.provider_symbol,
                interval=interval,
                limit=limit,
            )
            self.data = candles
            return candles

        response = self._get(
            "/api/v3/klines",
            {
                "symbol": asset.provider_symbol,
                "interval": interval,
                "limit": limit
            }
        )

        raw_data = response.json()

        candles = self._convert_candles(raw_data)

        self.data = candles

        return candles

    def _get_yahoo_candles(
        self,
        provider_symbol,
        interval="1m",
        limit=100,
    ):
        import urllib.parse

        range_by_interval = {
            "1m": "5d",
            "2m": "5d",
            "5m": "1mo",
            "15m": "1mo",
            "30m": "1mo",
            "60m": "3mo",
            "90m": "3mo",
            "1h": "3mo",
            "1d": "2y",
        }

        if interval not in range_by_interval:
            raise ValueError(
                f"Unsupported Yahoo interval '{interval}'"
            )

        encoded_symbol = urllib.parse.quote(
            provider_symbol,
            safe="",
        )

        response = requests.get(
            "https://query1.finance.yahoo.com/v8/finance/chart/"
            f"{encoded_symbol}",
            params={
                "range": range_by_interval[interval],
                "interval": interval,
                "includePrePost": "false",
                "events": "div,splits",
            },
            headers={
                "User-Agent": "AL-Trading-Agent-Paper/1.0",
            },
            timeout=10,
        )
        response.raise_for_status()

        payload = response.json()
        chart = payload.get("chart", {})
        result = chart.get("result") or []

        if not result:
            error = chart.get("error") or {}
            description = error.get("description", "empty response")
            raise ValueError(
                f"Yahoo Finance returned no candles for "
                f"{provider_symbol}: {description}"
            )

        chart_result = result[0]
        timestamps = chart_result.get("timestamp") or []
        quotes = (
            chart_result.get("indicators", {})
            .get("quote", [{}])[0]
        )

        candles = []

        for index, timestamp in enumerate(timestamps):
            values = {
                field: (quotes.get(field) or [None])[index]
                if index < len(quotes.get(field) or [])
                else None
                for field in ("open", "high", "low", "close", "volume")
            }

            if any(
                values[field] is None
                for field in ("open", "high", "low", "close")
            ):
                continue

            candles.append(
                Candle(
                    timestamp=int(timestamp) * 1000,
                    open=float(values["open"]),
                    high=float(values["high"]),
                    low=float(values["low"]),
                    close=float(values["close"]),
                    # Some Yahoo instruments, especially FX, do not publish
                    # volume. The candle is still valid for this strategy.
                    volume=float(values["volume"] or 0.0),
                )
            )

        if not candles:
            raise ValueError(
                f"Yahoo Finance returned no complete candles for "
                f"{provider_symbol}"
            )

        return candles[-limit:]

    def get_historical_candles(
        self,
        symbol="BTCUSDT",
        interval="1m",
        limit=1000
    ):
        asset = get_asset(symbol)

        if asset.provider == "yahoo":
            candles = self._get_yahoo_candles(
                provider_symbol=asset.provider_symbol,
                interval=interval,
                limit=limit,
            )
            self.data = candles
            return candles

        candles = []
        remaining = limit
        end_time = None

        while remaining > 0:
            batch_limit = min(1000, remaining)

            params = {
                "symbol": asset.provider_symbol,
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
