from datetime import datetime, timezone
from types import MappingProxyType, SimpleNamespace

from src.core.clock import FixedClock
from src.data.market_data import (
    DataQuality,
    ExecutionQuality,
    MarketSnapshot,
    ProviderStatus,
)
from src.execution.live_preflight import (
    PreflightAssetStatus,
    RealisticLivePreflight,
)
from src.execution.models import (
    PaperMode,
)
from src.market.market_session import (
    MarketSessionSnapshot,
    SessionQuality,
    SessionState,
)


NOW = datetime(
    2026,
    9,
    16,
    15,
    0,
    tzinfo=timezone.utc,
)


def snapshot(
    asset_id="BTCUSDT",
    *,
    quality=ExecutionQuality.REAL_BOOK,
    data_quality=DataQuality.REALTIME,
    delayed=False,
    bid=100.0,
    ask=101.0,
    last=100.5,
):
    if quality is ExecutionQuality.UNTRADEABLE:
        bid = None
        ask = None

    return MarketSnapshot(
        asset_id=asset_id,
        bid=bid,
        ask=ask,
        last=last,
        provider_timestamp=NOW,
        received_at=NOW,
        data_quality=data_quality,
        delayed=delayed,
        quote_age_seconds=0.0,
        provider_status=ProviderStatus.CONNECTED,
        execution_quality=quality,
    )


def session(
    asset_id="BTCUSDT",
    *,
    state=SessionState.OPEN,
    quality=SessionQuality.EXCHANGE_CALENDAR,
):
    return MarketSessionSnapshot(
        asset_id=asset_id,
        session_id="TEST",
        state=state,
        session_quality=quality,
        observed_at=NOW,
        timezone_name="UTC",
        local_time=NOW,
        reason="TEST",
        calendar_version="test-v1",
    )


class FakeMarketDataService:

    def __init__(
        self,
        *,
        snapshots=None,
        errors=None,
        duration=0.2,
        timed_out=False,
    ):
        self.snapshots = dict(
            snapshots or {}
        )
        self.errors = dict(
            errors or {}
        )
        self.duration = duration
        self.timed_out = timed_out
        self.calls = []

    def run_cycle(self, asset_ids):
        asset_ids = tuple(asset_ids)
        self.calls.append(asset_ids)

        return SimpleNamespace(
            snapshots=MappingProxyType(
                dict(self.snapshots)
            ),
            errors=MappingProxyType(
                dict(self.errors)
            ),
            duration_seconds=self.duration,
            timed_out=self.timed_out,
        )


class FakeSessionService:

    def __init__(
        self,
        sessions,
    ):
        self.sessions = dict(
            sessions
        )

    def get_session(
        self,
        asset_id,
        at,
    ):
        value = self.sessions[
            asset_id
        ]

        if isinstance(
            value,
            Exception,
        ):
            raise value

        return value


def test_live_preflight_real_book_open_is_ready():
    service = FakeMarketDataService(
        snapshots={
            "BTCUSDT": snapshot(),
        }
    )

    preflight = RealisticLivePreflight(
        market_data_service=service,
        market_session_service=FakeSessionService(
            {
                "BTCUSDT": session(),
            }
        ),
        clock=FixedClock(NOW),
        paper_mode=PaperMode.REALISTIC_PAPER,
    )

    cycle = preflight.run(
        ["BTCUSDT"]
    )

    result = cycle.results[
        "BTCUSDT"
    ]

    assert (
        result.status
        is PreflightAssetStatus.READY
    )

    assert result.allowed is True
    assert result.rejection_reason is None
    assert (
        result.execution_quality
        == "REAL_BOOK"
    )


def test_live_preflight_untradeable_is_blocked():
    preflight = RealisticLivePreflight(
        market_data_service=FakeMarketDataService(
            snapshots={
                "BTCUSDT": snapshot(
                    quality=(
                        ExecutionQuality.UNTRADEABLE
                    )
                ),
            }
        ),
        market_session_service=FakeSessionService(
            {
                "BTCUSDT": session(),
            }
        ),
        clock=FixedClock(NOW),
    )

    cycle = preflight.run(
        ["BTCUSDT"]
    )

    result = cycle.results[
        "BTCUSDT"
    ]

    assert (
        result.status
        is PreflightAssetStatus.BLOCKED
    )

    assert result.allowed is False
    assert (
        result.rejection_reason
        == "UNTRADEABLE"
    )


def test_live_preflight_delayed_realistic_is_blocked():
    preflight = RealisticLivePreflight(
        market_data_service=FakeMarketDataService(
            snapshots={
                "BTCUSDT": snapshot(
                    data_quality=(
                        DataQuality.DELAYED
                    ),
                    delayed=True,
                ),
            }
        ),
        market_session_service=FakeSessionService(
            {
                "BTCUSDT": session(),
            }
        ),
        clock=FixedClock(NOW),
        paper_mode=PaperMode.REALISTIC_PAPER,
    )

    cycle = preflight.run(
        ["BTCUSDT"]
    )

    result = cycle.results[
        "BTCUSDT"
    ]

    assert (
        result.status
        is PreflightAssetStatus.BLOCKED
    )

    assert (
        result.rejection_reason
        == "DELAYED_DATA"
    )


def test_live_preflight_delayed_research_is_labelled():
    preflight = RealisticLivePreflight(
        market_data_service=FakeMarketDataService(
            snapshots={
                "BTCUSDT": snapshot(
                    data_quality=(
                        DataQuality.DELAYED
                    ),
                    delayed=True,
                ),
            }
        ),
        market_session_service=FakeSessionService(
            {
                "BTCUSDT": session(),
            }
        ),
        clock=FixedClock(NOW),
        paper_mode=PaperMode.RESEARCH_PAPER,
    )

    cycle = preflight.run(
        ["BTCUSDT"]
    )

    result = cycle.results[
        "BTCUSDT"
    ]

    assert (
        result.status
        is PreflightAssetStatus.READY
    )

    assert (
        "DELAYED_DATA"
        in result.labels
    )


def test_live_preflight_unknown_session_is_blocked():
    preflight = RealisticLivePreflight(
        market_data_service=FakeMarketDataService(
            snapshots={
                "BTCUSDT": snapshot(),
            }
        ),
        market_session_service=FakeSessionService(
            {
                "BTCUSDT": session(
                    state=SessionState.UNKNOWN,
                    quality=SessionQuality.UNKNOWN,
                ),
            }
        ),
        clock=FixedClock(NOW),
    )

    cycle = preflight.run(
        ["BTCUSDT"]
    )

    result = cycle.results[
        "BTCUSDT"
    ]

    assert (
        result.status
        is PreflightAssetStatus.BLOCKED
    )

    assert (
        result.rejection_reason
        == "SESSION_UNAVAILABLE"
    )


def test_live_preflight_data_error_is_isolated():
    preflight = RealisticLivePreflight(
        market_data_service=FakeMarketDataService(
            snapshots={
                "BTCUSDT": snapshot(),
            },
            errors={
                "AAPL": "PROVIDER_TIMEOUT",
            },
        ),
        market_session_service=FakeSessionService(
            {
                "BTCUSDT": session(),
            }
        ),
        clock=FixedClock(NOW),
    )

    cycle = preflight.run(
        [
            "BTCUSDT",
            "AAPL",
        ]
    )

    assert (
        cycle.results[
            "BTCUSDT"
        ].status
        is PreflightAssetStatus.READY
    )

    assert (
        cycle.results[
            "AAPL"
        ].status
        is PreflightAssetStatus.DATA_ERROR
    )

    assert (
        cycle.results[
            "AAPL"
        ].error
        == "PROVIDER_TIMEOUT"
    )


def test_live_preflight_session_error_is_isolated():
    preflight = RealisticLivePreflight(
        market_data_service=FakeMarketDataService(
            snapshots={
                "BTCUSDT": snapshot(),
            }
        ),
        market_session_service=FakeSessionService(
            {
                "BTCUSDT": RuntimeError(
                    "calendar failed"
                ),
            }
        ),
        clock=FixedClock(NOW),
    )

    cycle = preflight.run(
        ["BTCUSDT"]
    )

    result = cycle.results[
        "BTCUSDT"
    ]

    assert (
        result.status
        is PreflightAssetStatus.SESSION_ERROR
    )

    assert (
        "calendar failed"
        in result.error
    )


def test_live_preflight_propagates_cycle_metadata():
    preflight = RealisticLivePreflight(
        market_data_service=FakeMarketDataService(
            errors={
                "BTCUSDT": "CYCLE_TIMEOUT",
            },
            duration=20.1,
            timed_out=True,
        ),
        market_session_service=FakeSessionService(
            {}
        ),
        clock=FixedClock(NOW),
    )

    cycle = preflight.run(
        ["BTCUSDT"]
    )

    assert cycle.timed_out is True
    assert cycle.duration_seconds == 20.1
