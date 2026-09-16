from datetime import datetime, timezone
from threading import Barrier

import pytest

from src.core.clock import SystemClock
from src.data.market_data import (
    DataQuality,
    ExecutionQuality,
    MarketSnapshot,
    ProviderStatus,
)
from src.data.parallel_market_data_service import (
    ParallelMarketDataService,
)
from src.execution.live_preflight import (
    build_live_preflight,
)


NOW = datetime(
    2026,
    9,
    16,
    15,
    0,
    tzinfo=timezone.utc,
)


def make_snapshot(asset_id):
    return MarketSnapshot(
        asset_id=asset_id,
        bid=100.0,
        ask=101.0,
        last=100.5,
        provider_timestamp=NOW,
        received_at=NOW,
        data_quality=DataQuality.REALTIME,
        delayed=False,
        quote_age_seconds=0.0,
        provider_status=ProviderStatus.CONNECTED,
        execution_quality=ExecutionQuality.REAL_BOOK,
    )


class ImmediateProvider:

    def get_market_snapshot(
        self,
        asset_id,
        *,
        stale_after_seconds,
        deadline_monotonic,
    ):
        return make_snapshot(
            asset_id
        )


class ErrorProvider:

    def get_market_snapshot(
        self,
        asset_id,
        *,
        stale_after_seconds,
        deadline_monotonic,
    ):
        if asset_id == "BAD":
            raise RuntimeError(
                "provider failed"
            )

        if asset_id == "TIMEOUT":
            raise TimeoutError(
                "provider deadline exceeded"
            )

        return make_snapshot(
            asset_id
        )


class BarrierProvider:
    """
    Both calls must reach the provider concurrently.
    A sequential implementation breaks the barrier.
    """

    def __init__(self):
        self.barrier = Barrier(2)

    def get_market_snapshot(
        self,
        asset_id,
        *,
        stale_after_seconds,
        deadline_monotonic,
    ):
        self.barrier.wait(
            timeout=2.0
        )

        return make_snapshot(
            asset_id
        )


def test_parallel_service_returns_all_snapshots():
    service = ParallelMarketDataService(
        ImmediateProvider(),
        clock=SystemClock(),
        cycle_timeout_seconds=2.0,
        per_asset_timeout_seconds=1.0,
        max_workers=2,
    )

    cycle = service.run_cycle(
        [
            "BTCUSDT",
            "ETHUSDT",
        ]
    )

    assert set(
        cycle.snapshots
    ) == {
        "BTCUSDT",
        "ETHUSDT",
    }

    assert cycle.errors == {}
    assert cycle.timed_out is False


def test_parallel_service_actually_overlaps_provider_calls():
    service = ParallelMarketDataService(
        BarrierProvider(),
        clock=SystemClock(),
        cycle_timeout_seconds=2.0,
        per_asset_timeout_seconds=1.5,
        max_workers=2,
    )

    cycle = service.run_cycle(
        [
            "BTCUSDT",
            "ETHUSDT",
        ]
    )

    assert set(
        cycle.snapshots
    ) == {
        "BTCUSDT",
        "ETHUSDT",
    }

    assert cycle.errors == {}


def test_parallel_service_isolates_provider_errors():
    service = ParallelMarketDataService(
        ErrorProvider(),
        cycle_timeout_seconds=2.0,
        per_asset_timeout_seconds=1.0,
        max_workers=3,
    )

    cycle = service.run_cycle(
        [
            "GOOD",
            "BAD",
            "TIMEOUT",
        ]
    )

    assert "GOOD" in cycle.snapshots

    assert (
        cycle.errors["BAD"]
        == "RuntimeError: provider failed"
    )

    assert (
        cycle.errors["TIMEOUT"]
        == "PROVIDER_TIMEOUT"
    )


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "max_workers": 0,
        },
        {
            "per_asset_timeout_seconds": 0,
        },
        {
            "cycle_timeout_seconds": 0,
        },
    ],
)
def test_parallel_service_rejects_invalid_limits(
    kwargs,
):
    with pytest.raises(
        ValueError
    ):
        ParallelMarketDataService(
            ImmediateProvider(),
            **kwargs,
        )


def test_realistic_live_builder_uses_parallel_service():
    preflight = build_live_preflight()

    service = (
        preflight.market_data_service
    )

    assert isinstance(
        service,
        ParallelMarketDataService,
    )

    assert service.max_workers == 5

    assert (
        service.per_asset_timeout_seconds
        == 8.0
    )

    assert (
        service.cycle_timeout_seconds
        == 20.0
    )
