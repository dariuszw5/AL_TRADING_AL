import time
import json
import requests
from datetime import datetime, timezone

from src.data.candle import Candle
from src.data.assets import get_asset
from src.core.clock import (
    Clock,
    SystemClock,
)
from src.data.market_data import (
    ExecutionQuality,
    MarketSnapshot,
    ProviderHealth,
    ProviderStatus,
    classify_data_quality,
)


class DataProvider:
    BASE_URL = "https://data-api.binance.vision"

    def __init__(
        self,
        *,
        clock: Clock | None = None,
        request_timeout_seconds=10.0,
    ):
        if request_timeout_seconds <= 0:
            raise ValueError(
                "request_timeout_seconds must be positive"
            )

        self.data = []
        self.clock = clock or SystemClock()
        self.request_timeout_seconds = float(
            request_timeout_seconds
        )
        self._provider_health = {}

    def _remaining_timeout(
        self,
        deadline_monotonic=None,
    ):
        if deadline_monotonic is None:
            return self.request_timeout_seconds

        remaining = (
            float(deadline_monotonic)
            - self.clock.monotonic()
        )

        if remaining <= 0.0:
            raise TimeoutError(
                "Provider request deadline exceeded"
            )

        return max(
            0.001,
            min(
                self.request_timeout_seconds,
                remaining,
            ),
        )

    def _request_get(
        self,
        url,
        *,
        params=None,
        headers=None,
        attempts=3,
        deadline_monotonic=None,
    ):
        last_error = None

        for attempt in range(attempts):
            timeout = self._remaining_timeout(
                deadline_monotonic
            )

            try:
                response = requests.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=timeout,
                )

                response.raise_for_status()
                return response

            except requests.exceptions.RequestException as error:
                last_error = error

                if attempt >= attempts - 1:
                    break

                sleep_for = 1.0

                if deadline_monotonic is not None:
                    remaining = (
                        deadline_monotonic
                        - self.clock.monotonic()
                    )

                    if remaining <= 0.0:
                        raise TimeoutError(
                            "Provider request deadline exceeded"
                        ) from error

                    sleep_for = min(
                        sleep_for,
                        remaining,
                    )

                if sleep_for > 0.0:
                    time.sleep(sleep_for)

        if last_error is not None:
            raise last_error

        raise RuntimeError(
            "Provider request failed"
        )

    def _get(
        self,
        endpoint,
        params,
        *,
        deadline_monotonic=None,
    ):
        return self._request_get(
            f"{self.BASE_URL}{endpoint}",
            params=params,
            deadline_monotonic=deadline_monotonic,
        )

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


    def _get_yahoo_response(
        self,
        *,
        provider_symbol,
        interval="1m",
        range_value="1d",
        deadline_monotonic=None,
    ):
        import urllib.parse

        encoded_symbol = urllib.parse.quote(
            provider_symbol,
            safe="",
        )

        return self._request_get(
            "https://query1.finance.yahoo.com/"
            "v8/finance/chart/"
            f"{encoded_symbol}",
            params={
                "range": range_value,
                "interval": interval,
                "includePrePost": "false",
                "events": "div,splits",
            },
            headers={
                "User-Agent": (
                    "AL-Trading-Agent-Paper/1.0"
                ),
            },
            deadline_monotonic=(
                deadline_monotonic
            ),
        )

    @staticmethod
    def _yahoo_result(
        response,
        provider_symbol,
    ):
        payload = response.json()

        chart = payload.get(
            "chart",
            {},
        )

        results = (
            chart.get("result")
            or []
        )

        if not results:
            error = (
                chart.get("error")
                or {}
            )

            description = error.get(
                "description",
                "empty response",
            )

            raise ValueError(
                "Yahoo Finance returned no data "
                f"for {provider_symbol}: "
                f"{description}"
            )

        return results[0]

    @staticmethod
    def _optional_positive(value):
        try:
            result = float(value)
        except (
            TypeError,
            ValueError,
        ):
            return None

        if result <= 0.0:
            return None

        return result

    def _record_health(
        self,
        *,
        asset,
        status,
        started_monotonic,
        error=None,
    ):
        checked_at = self.clock.now()

        latency_ms = max(
            0.0,
            (
                self.clock.monotonic()
                - started_monotonic
            )
            * 1000.0,
        )

        previous = self._provider_health.get(
            asset.asset_id
        )

        success = (
            status
            is ProviderStatus.CONNECTED
        )

        health = ProviderHealth(
            asset_id=asset.asset_id,
            provider=asset.provider,
            status=status,
            checked_at=checked_at,
            last_success_at=(
                checked_at
                if success
                else (
                    previous.last_success_at
                    if previous
                    else None
                )
            ),
            latency_ms=latency_ms,
            consecutive_failures=(
                0
                if success
                else (
                    (
                        previous.consecutive_failures
                        if previous
                        else 0
                    )
                    + 1
                )
            ),
            last_error=(
                None
                if success
                else str(error)
            ),
        )

        self._provider_health[
            asset.asset_id
        ] = health

        return health

    def get_provider_health(
        self,
        symbol,
    ):
        asset = get_asset(symbol)

        return self._provider_health.get(
            asset.asset_id
        )

    def get_market_snapshot(
        self,
        symbol,
        *,
        stale_after_seconds=120.0,
        deadline_monotonic=None,
    ):
        asset = get_asset(symbol)

        started = self.clock.monotonic()

        try:
            if asset.provider == "binance":
                snapshot = (
                    self._get_binance_snapshot(
                        asset,
                        stale_after_seconds=(
                            stale_after_seconds
                        ),
                        deadline_monotonic=(
                            deadline_monotonic
                        ),
                    )
                )

            elif asset.provider == "yahoo":
                snapshot = (
                    self._get_yahoo_snapshot(
                        asset,
                        stale_after_seconds=(
                            stale_after_seconds
                        ),
                        deadline_monotonic=(
                            deadline_monotonic
                        ),
                    )
                )

            else:
                raise ValueError(
                    "Unsupported provider "
                    f"'{asset.provider}'"
                )

            self._record_health(
                asset=asset,
                status=ProviderStatus.CONNECTED,
                started_monotonic=started,
            )

            return snapshot

        except Exception as exc:
            status = ProviderStatus.ERROR

            if isinstance(
                exc,
                requests.exceptions.HTTPError,
            ):
                response = getattr(
                    exc,
                    "response",
                    None,
                )

                if (
                    response is not None
                    and response.status_code == 429
                ):
                    status = (
                        ProviderStatus.RATE_LIMITED
                    )

            self._record_health(
                asset=asset,
                status=status,
                started_monotonic=started,
                error=exc,
            )

            raise

    def _get_binance_snapshot(
        self,
        asset,
        *,
        stale_after_seconds,
        deadline_monotonic,
    ):
        book_response = self._get(
            "/api/v3/ticker/bookTicker",
            {
                "symbol": (
                    asset.provider_symbol
                )
            },
            deadline_monotonic=(
                deadline_monotonic
            ),
        )

        ticker_response = self._get(
            "/api/v3/ticker/24hr",
            {
                "symbol": (
                    asset.provider_symbol
                )
            },
            deadline_monotonic=(
                deadline_monotonic
            ),
        )

        book = book_response.json()
        ticker = ticker_response.json()

        bid = self._optional_positive(
            book.get("bidPrice")
        )

        ask = self._optional_positive(
            book.get("askPrice")
        )

        last = self._optional_positive(
            ticker.get("lastPrice")
        )

        provider_timestamp = None

        close_time = ticker.get(
            "closeTime"
        )

        if isinstance(
            close_time,
            (int, float),
        ):
            provider_timestamp = (
                datetime.fromtimestamp(
                    close_time / 1000.0,
                    tz=timezone.utc,
                )
            )

        received_at = self.clock.now()

        (
            data_quality,
            delayed,
            quote_age,
        ) = classify_data_quality(
            provider_timestamp=(
                provider_timestamp
            ),
            received_at=received_at,
            delay_hint_seconds=0.0,
            stale_after_seconds=(
                stale_after_seconds
            ),
        )

        execution_quality = (
            ExecutionQuality.REAL_BOOK
            if (
                bid is not None
                and ask is not None
            )
            else ExecutionQuality.UNTRADEABLE
        )

        return MarketSnapshot(
            asset_id=asset.asset_id,
            bid=bid,
            ask=ask,
            last=last,
            provider_timestamp=(
                provider_timestamp
            ),
            received_at=received_at,
            data_quality=data_quality,
            delayed=delayed,
            quote_age_seconds=quote_age,
            provider_status=(
                ProviderStatus.CONNECTED
            ),
            execution_quality=(
                execution_quality
            ),
            metadata=(
                (
                    "provider",
                    asset.provider,
                ),
                (
                    "provider_symbol",
                    asset.provider_symbol,
                ),
            ),
        )

    def _get_yahoo_snapshot(
        self,
        asset,
        *,
        stale_after_seconds,
        deadline_monotonic,
    ):
        response = self._get_yahoo_response(
            provider_symbol=(
                asset.provider_symbol
            ),
            interval=asset.interval,
            range_value="1d",
            deadline_monotonic=(
                deadline_monotonic
            ),
        )

        result = self._yahoo_result(
            response,
            asset.provider_symbol,
        )

        meta = (
            result.get("meta")
            or {}
        )

        timestamps = (
            result.get("timestamp")
            or []
        )

        quote_sets = (
            result.get(
                "indicators",
                {},
            )
            .get(
                "quote",
                [{}],
            )
        )

        quote = (
            quote_sets[0]
            if quote_sets
            else {}
        ) or {}

        closes = (
            quote.get("close")
            or []
        )

        latest_close = None

        for value in reversed(closes):
            if value is not None:
                latest_close = value
                break

        bid = self._optional_positive(
            meta.get("bid")
        )

        ask = self._optional_positive(
            meta.get("ask")
        )

        last = self._optional_positive(
            meta.get(
                "regularMarketPrice"
            )
        )

        if last is None:
            last = self._optional_positive(
                latest_close
            )

        provider_timestamp = None

        market_time = meta.get(
            "regularMarketTime"
        )

        if isinstance(
            market_time,
            (int, float),
        ):
            provider_timestamp = (
                datetime.fromtimestamp(
                    market_time,
                    tz=timezone.utc,
                )
            )

        elif timestamps:
            provider_timestamp = (
                datetime.fromtimestamp(
                    max(timestamps),
                    tz=timezone.utc,
                )
            )

        delayed_by = meta.get(
            "exchangeDataDelayedBy"
        )

        if not isinstance(
            delayed_by,
            (int, float),
        ):
            delayed_by = None

        received_at = self.clock.now()

        (
            data_quality,
            delayed,
            quote_age,
        ) = classify_data_quality(
            provider_timestamp=(
                provider_timestamp
            ),
            received_at=received_at,
            delay_hint_seconds=delayed_by,
            stale_after_seconds=(
                stale_after_seconds
            ),
        )

        # Phase 06 only classifies execution quality.
        # No simulated/derived spread is introduced here.
        execution_quality = (
            ExecutionQuality.REAL_BOOK
            if (
                bid is not None
                and ask is not None
            )
            else ExecutionQuality.UNTRADEABLE
        )

        return MarketSnapshot(
            asset_id=asset.asset_id,
            bid=bid,
            ask=ask,
            last=last,
            provider_timestamp=(
                provider_timestamp
            ),
            received_at=received_at,
            data_quality=data_quality,
            delayed=delayed,
            quote_age_seconds=quote_age,
            provider_status=(
                ProviderStatus.CONNECTED
            ),
            execution_quality=(
                execution_quality
            ),
            metadata=(
                (
                    "provider",
                    asset.provider,
                ),
                (
                    "provider_symbol",
                    asset.provider_symbol,
                ),
                (
                    "api_status",
                    (
                        "UNOFFICIAL / "
                        "DEGRADED_BY_DESIGN"
                    ),
                ),
            ),
        )
