import json
import math
import time
import urllib.parse

import requests

from src.data.assets import get_asset
from src.data.candle import Candle


class DataProvider:
    BINANCE_BASE_URL = "https://data-api.binance.vision"
    YAHOO_BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart"

    def __init__(self):
        self.data = []

    def _request(self, url, *, params=None, headers=None):
        last_error = None

        for attempt in range(3):
            try:
                response = requests.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=10,
                )
                response.raise_for_status()
                return response
            except requests.exceptions.RequestException as error:
                last_error = error
                if attempt < 2:
                    time.sleep(0.5)

        raise last_error

    def _get_binance(self, endpoint, params):
        return self._request(
            f"{self.BINANCE_BASE_URL}{endpoint}",
            params=params,
        )

    @staticmethod
    def _validate_candles(candles, *, symbol):
        if not candles:
            raise ValueError(f"No complete candles returned for {symbol}")

        previous_timestamp = None
        for candle in candles:
            values = (
                candle.open,
                candle.high,
                candle.low,
                candle.close,
            )
            if not all(math.isfinite(float(value)) for value in values):
                raise ValueError(f"Non-finite OHLC value for {symbol}")
            if candle.high < max(candle.open, candle.close):
                raise ValueError(f"Invalid candle high for {symbol}")
            if candle.low > min(candle.open, candle.close):
                raise ValueError(f"Invalid candle low for {symbol}")
            if candle.high < candle.low:
                raise ValueError(f"Invalid candle range for {symbol}")
            if previous_timestamp is not None and candle.timestamp <= previous_timestamp:
                raise ValueError(f"Non-monotonic candle timestamps for {symbol}")
            previous_timestamp = candle.timestamp

        return candles

    def _convert_candles(self, raw_data, *, symbol):
        candles = [
            Candle(
                timestamp=int(item[0]),
                open=float(item[1]),
                high=float(item[2]),
                low=float(item[3]),
                close=float(item[4]),
                volume=float(item[5]),
            )
            for item in raw_data
        ]
        return self._validate_candles(candles, symbol=symbol)

    def save_candles(self, candles, file_path):
        data = [
            {
                "timestamp": candle.timestamp,
                "open": candle.open,
                "high": candle.high,
                "low": candle.low,
                "close": candle.close,
                "volume": candle.volume,
            }
            for candle in candles
        ]

        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=2)

    def load_candles(self, file_path):
        with open(file_path, "r", encoding="utf-8-sig") as file:
            data = json.load(file)

        candles = [
            Candle(
                timestamp=int(item["timestamp"]),
                open=float(item["open"]),
                high=float(item["high"]),
                low=float(item["low"]),
                close=float(item["close"]),
                volume=float(item["volume"]),
            )
            for item in data
        ]

        if not candles:
            self.data = []
            return self.data

        self.data = self._validate_candles(candles, symbol=str(file_path))
        return self.data

    def get_candles(self, symbol="BTCUSDT", interval="1m", limit=100):
        asset = get_asset(symbol)

        if asset.provider == "yahoo":
            candles = self._get_yahoo_candles(
                provider_symbol=asset.provider_symbol,
                interval=interval,
                limit=limit,
                asset_symbol=asset.symbol,
            )
        else:
            response = self._get_binance(
                "/api/v3/klines",
                {
                    "symbol": asset.provider_symbol,
                    "interval": interval,
                    "limit": limit,
                },
            )
            candles = self._convert_candles(
                response.json(),
                symbol=asset.symbol,
            )

        self.data = candles
        return candles

    def _get_yahoo_candles(
        self,
        provider_symbol,
        interval="1m",
        limit=100,
        asset_symbol=None,
    ):
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
            raise ValueError(f"Unsupported Yahoo interval '{interval}'")

        encoded_symbol = urllib.parse.quote(provider_symbol, safe="")
        response = self._request(
            f"{self.YAHOO_BASE_URL}/{encoded_symbol}",
            params={
                "range": range_by_interval[interval],
                "interval": interval,
                "includePrePost": "false",
                "events": "div,splits",
            },
            headers={"User-Agent": "AL-Trading-Agent-Paper/1.0"},
        )

        payload = response.json()
        chart = payload.get("chart", {})
        result = chart.get("result") or []

        if not result:
            error = chart.get("error") or {}
            description = error.get("description", "empty response")
            raise ValueError(
                f"Yahoo Finance returned no candles for {provider_symbol}: {description}"
            )

        chart_result = result[0]
        timestamps = chart_result.get("timestamp") or []
        quotes = chart_result.get("indicators", {}).get("quote", [{}])[0]

        candles = []
        for index, timestamp in enumerate(timestamps):
            values = {}
            for field in ("open", "high", "low", "close", "volume"):
                field_values = quotes.get(field) or []
                values[field] = field_values[index] if index < len(field_values) else None

            if any(values[field] is None for field in ("open", "high", "low", "close")):
                continue

            candles.append(
                Candle(
                    timestamp=int(timestamp) * 1000,
                    open=float(values["open"]),
                    high=float(values["high"]),
                    low=float(values["low"]),
                    close=float(values["close"]),
                    volume=float(values["volume"] or 0.0),
                )
            )

        candles = candles[-limit:]
        return self._validate_candles(
            candles,
            symbol=asset_symbol or provider_symbol,
        )

    def get_historical_candles(self, symbol="BTCUSDT", interval="1m", limit=1000):
        asset = get_asset(symbol)

        if asset.provider == "yahoo":
            candles = self._get_yahoo_candles(
                provider_symbol=asset.provider_symbol,
                interval=interval,
                limit=limit,
                asset_symbol=asset.symbol,
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
                "limit": batch_limit,
            }
            if end_time is not None:
                params["endTime"] = end_time

            response = self._get_binance("/api/v3/klines", params)
            raw_data = response.json()
            if not raw_data:
                break

            batch = self._convert_candles(raw_data, symbol=asset.symbol)
            candles = batch + candles
            remaining -= len(batch)
            end_time = int(raw_data[0][0]) - 1

            if len(batch) < batch_limit:
                break

        self.data = self._validate_candles(candles, symbol=asset.symbol)
        return self.data
