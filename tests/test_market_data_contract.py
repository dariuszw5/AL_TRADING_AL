from datetime import datetime, timedelta, timezone

import pytest

from src.core.clock import (
    FixedClock,
    SystemClock,
)
from src.data.candle import Candle
from src.data.data_provider import DataProvider
from src.data.market_data import (
    DataQuality,
    ExecutionQuality,
    MarketSnapshot,
    ProviderStatus,
    classify_data_quality,
    normalize_candles,
)
from src.data.market_data_service import (
    CycleInProgressError,
    MarketDataService,
)


UTC_NOW = datetime(
    2026,
    9,
    16,
    14,
    0,
    tzinfo=timezone.utc,
)


class FakeResponse:

    def __init__(self, data):
        self._data = data
        self.status_code = 200

    def json(self):
        return self._data

    def raise_for_status(self):
        return None


def snapshot_for(
    asset_id,
    now=UTC_NOW,
):
    return MarketSnapshot(
        asset_id=asset_id,
        bid=100.0,
        ask=101.0,
        last=100.5,
        provider_timestamp=now,
        received_at=now,
        data_quality=DataQuality.REALTIME,
        delayed=False,
        quote_age_seconds=0.0,
        provider_status=ProviderStatus.CONNECTED,
        execution_quality=ExecutionQuality.REAL_BOOK,
    )


def test_system_clock_returns_utc_aware_time():
    now = SystemClock().now()

    assert now.tzinfo is not None
    assert now.utcoffset().total_seconds() == 0


def test_fixed_clock_is_deterministic():
    clock = FixedClock(
        UTC_NOW,
        monotonic_value=10.0,
    )

    clock.advance(5.0)

    assert clock.now() == (
        UTC_NOW
        + timedelta(seconds=5)
    )
    assert clock.monotonic() == 15.0


def test_normalized_candles_reject_duplicate_timestamp():
    candles = [
        Candle(
            1_700_000_000_000,
            100,
            102,
            99,
            101,
            10,
        ),
        Candle(
            1_700_000_000_000,
            101,
            103,
            100,
            102,
            11,
        ),
    ]

    with pytest.raises(
        ValueError,
        match="Duplicate or out-of-order",
    ):
        normalize_candles(candles)


def test_normalized_candle_uses_utc_datetime():
    candle = Candle(
        1_700_000_000_000,
        100,
        102,
        99,
        101,
        10,
    )

    normalized = normalize_candles(
        [candle]
    )[0]

    assert (
        normalized.timestamp.utcoffset()
        .total_seconds()
        == 0
    )


def test_unknown_delay_is_not_reported_as_realtime():
    quality, delayed, age = (
        classify_data_quality(
            provider_timestamp=(
                UTC_NOW
                - timedelta(seconds=10)
            ),
            received_at=UTC_NOW,
            delay_hint_seconds=None,
            stale_after_seconds=120,
        )
    )

    assert quality is DataQuality.UNKNOWN
    assert delayed is None
    assert age == 10


def test_old_quote_is_stale_even_if_delay_unknown():
    quality, delayed, age = (
        classify_data_quality(
            provider_timestamp=(
                UTC_NOW
                - timedelta(minutes=5)
            ),
            received_at=UTC_NOW,
            delay_hint_seconds=None,
            stale_after_seconds=120,
        )
    )

    assert quality is DataQuality.STALE
    assert delayed is True
    assert age == 300


def test_real_book_requires_bid_and_ask():
    with pytest.raises(
        ValueError,
        match="REAL_BOOK requires",
    ):
        MarketSnapshot(
            asset_id="BTCUSDT",
            bid=None,
            ask=101.0,
            last=100.0,
            provider_timestamp=UTC_NOW,
            received_at=UTC_NOW,
            data_quality=DataQuality.REALTIME,
            delayed=False,
            quote_age_seconds=0.0,
            provider_status=ProviderStatus.CONNECTED,
            execution_quality=ExecutionQuality.REAL_BOOK,
        )


def test_binance_snapshot_uses_real_book(monkeypatch):
    clock = FixedClock(
        UTC_NOW,
        monotonic_value=1.0,
    )

    provider = DataProvider(
        clock=clock
    )

    timestamp_ms = int(
        UTC_NOW.timestamp()
        * 1000
    )

    def fake_get(
        endpoint,
        params,
        *,
        deadline_monotonic=None,
    ):
        if endpoint.endswith(
            "bookTicker"
        ):
            return FakeResponse(
                {
                    "bidPrice": "100.0",
                    "askPrice": "101.0",
                }
            )

        if endpoint.endswith(
            "24hr"
        ):
            return FakeResponse(
                {
                    "lastPrice": "100.5",
                    "closeTime": timestamp_ms,
                }
            )

        raise AssertionError(endpoint)

    monkeypatch.setattr(
        provider,
        "_get",
        fake_get,
    )

    result = provider.get_market_snapshot(
        "BTCUSDT"
    )

    assert result.bid == 100.0
    assert result.ask == 101.0
    assert result.last == 100.5

    assert (
        result.execution_quality
        is ExecutionQuality.REAL_BOOK
    )

    assert (
        result.data_quality
        is DataQuality.REALTIME
    )

    assert result.delayed is False

    health = provider.get_provider_health(
        "BTCUSDT"
    )

    assert (
        health.status
        is ProviderStatus.CONNECTED
    )


def test_yahoo_without_bid_ask_is_not_real_book(
    monkeypatch,
):
    clock = FixedClock(
        UTC_NOW,
        monotonic_value=1.0,
    )

    provider = DataProvider(
        clock=clock
    )

    timestamp = int(
        UTC_NOW.timestamp()
    )

    response = FakeResponse(
        {
            "chart": {
                "result": [
                    {
                        "meta": {
                            "regularMarketPrice": 250.0,
                            "regularMarketTime": timestamp,
                            "exchangeName": "TEST",
                        },
                        "timestamp": [
                            timestamp
                        ],
                        "indicators": {
                            "quote": [
                                {
                                    "close": [
                                        250.0
                                    ],
                                    "volume": [
                                        10
                                    ],
                                }
                            ]
                        },
                    }
                ],
                "error": None,
            }
        }
    )

    monkeypatch.setattr(
        provider,
        "_get_yahoo_response",
        lambda **kwargs: response,
    )

    result = provider.get_market_snapshot(
        "AAPL"
    )

    assert result.bid is None
    assert result.ask is None
    assert result.last == 250.0

    assert (
        result.execution_quality
        is ExecutionQuality.UNTRADEABLE
    )

    assert (
        result.data_quality
        is DataQuality.UNKNOWN
    )

    assert result.delayed is None


def test_market_data_cycle_isolates_asset_failure():
    class FakeProvider:

        def get_market_snapshot(
            self,
            asset_id,
            **kwargs,
        ):
            if asset_id == "ETHUSDT":
                raise TimeoutError(
                    "provider timeout"
                )

            return snapshot_for(
                asset_id
            )

    service = MarketDataService(
        FakeProvider(),
        clock=FixedClock(
            UTC_NOW
        ),
    )

    result = service.run_cycle(
        [
            "BTCUSDT",
            "ETHUSDT",
            "SOLUSDT",
        ]
    )

    assert set(
        result.snapshots
    ) == {
        "BTCUSDT",
        "SOLUSDT",
    }

    assert "ETHUSDT" in result.errors
    assert result.timed_out is False


def test_cycle_lock_blocks_overlap():
    service = MarketDataService(
        object(),
        clock=FixedClock(
            UTC_NOW
        ),
    )

    assert service._cycle_lock.acquire(
        blocking=False
    )

    try:
        with pytest.raises(
            CycleInProgressError
        ):
            service.run_cycle(
                ["BTCUSDT"]
            )
    finally:
        service._cycle_lock.release()


def test_cycle_timeout_stops_remaining_assets():
    clock = FixedClock(
        UTC_NOW
    )

    class SlowProvider:

        def get_market_snapshot(
            self,
            asset_id,
            **kwargs,
        ):
            clock.advance(6.0)

            return snapshot_for(
                asset_id,
                now=clock.now(),
            )

    service = MarketDataService(
        SlowProvider(),
        clock=clock,
        cycle_timeout_seconds=5.0,
    )

    result = service.run_cycle(
        [
            "BTCUSDT",
            "ETHUSDT",
        ]
    )

    assert result.timed_out is True

    assert (
        result.errors["BTCUSDT"]
        == "CYCLE_TIMEOUT"
    )

    assert (
        result.errors["ETHUSDT"]
        == "CYCLE_TIMEOUT"
    )

    assert not result.snapshots
    assert result.duration_seconds == 6.0
