from datetime import datetime, timezone
from types import SimpleNamespace

from src.core.clock import FixedClock
from src.data.market_data import (
    DataQuality,
    ExecutionQuality,
    MarketSnapshot,
    ProviderStatus,
)
from src.execution.models import (
    OrderIntent,
    OrderSide,
    OrderStatus,
    PaperMode,
    PositionStatus,
)
from src.execution.paper_broker import PaperBroker
from src.execution.runtime import (
    ExecutionDecision,
    RealisticPaperRuntime,
    RuntimeAssetStatus,
)
from src.execution.slippage import FixedBpsSlippage
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


class FakeAsset:

    def __init__(self, asset_id):
        self.asset_id = asset_id
        self.allow_long = True
        self.allow_short = False
        self.short_mechanism = "NONE"
        self.short_financing_model = None


def asset_resolver(asset_id):
    return FakeAsset(asset_id)


def snapshot(
    asset_id,
    *,
    bid=100.0,
    ask=101.0,
    last=100.5,
):
    return MarketSnapshot(
        asset_id=asset_id,
        bid=bid,
        ask=ask,
        last=last,
        provider_timestamp=NOW,
        received_at=NOW,
        data_quality=DataQuality.REALTIME,
        delayed=False,
        quote_age_seconds=0.0,
        provider_status=ProviderStatus.CONNECTED,
        execution_quality=ExecutionQuality.REAL_BOOK,
    )


class FakeMarketDataService:

    def __init__(
        self,
        *,
        snapshots=None,
        errors=None,
        timed_out=False,
    ):
        self.snapshots = dict(
            snapshots or {}
        )

        self.errors = dict(
            errors or {}
        )

        self.timed_out = timed_out
        self.calls = []

    def run_cycle(self, asset_ids):
        asset_ids = tuple(asset_ids)
        self.calls.append(asset_ids)

        return SimpleNamespace(
            snapshots=dict(
                self.snapshots
            ),
            errors=dict(
                self.errors
            ),
            duration_seconds=0.25,
            timed_out=self.timed_out,
        )


class FakeSessionService:

    def __init__(
        self,
        *,
        state=SessionState.OPEN,
        fail_assets=None,
    ):
        self.state = state
        self.fail_assets = set(
            fail_assets or ()
        )
        self.calls = []

    def get_session(
        self,
        asset_id,
        at,
    ):
        self.calls.append(
            (
                asset_id,
                at,
            )
        )

        if asset_id in self.fail_assets:
            raise RuntimeError(
                "session unavailable"
            )

        return MarketSessionSnapshot(
            asset_id=asset_id,
            session_id="TEST_SESSION",
            state=self.state,
            session_quality=(
                SessionQuality.EXCHANGE_CALENDAR
            ),
            observed_at=at,
            timezone_name="UTC",
            local_time=at,
            reason="TEST",
            calendar_version="test-v1",
        )


class QueueDecisionProvider:

    def __init__(self, decisions):
        self.decisions = list(
            decisions
        )
        self.calls = []

    def __call__(
        self,
        *,
        asset_id,
        snapshot,
        position,
    ):
        self.calls.append(
            (
                asset_id,
                snapshot,
                position,
            )
        )

        if not self.decisions:
            return None

        return self.decisions.pop(0)


def make_broker():
    return PaperBroker(
        clock=FixedClock(NOW),
        asset_resolver=asset_resolver,
        slippage_model=FixedBpsSlippage(
            0.0
        ),
        trading_fee_rate=0.0,
    )


def entry_decision():
    return ExecutionDecision(
        side=OrderSide.BUY,
        intent=OrderIntent.ENTRY,
        quantity=2.0,
        stop_loss=95.0,
        take_profit=110.0,
        signal_reference="test-buy",
    )


def exit_decision():
    return ExecutionDecision(
        side=OrderSide.SELL,
        intent=OrderIntent.EXIT,
        quantity=2.0,
        exit_reason="TIME_EXIT",
        signal_reference="test-exit",
    )


def test_runtime_opens_position_through_paper_broker():
    data = FakeMarketDataService(
        snapshots={
            "TEST": snapshot("TEST"),
        }
    )

    sessions = FakeSessionService()

    decisions = QueueDecisionProvider(
        [
            entry_decision(),
        ]
    )

    runtime = RealisticPaperRuntime(
        market_data_service=data,
        market_session_service=sessions,
        broker=make_broker(),
        decision_provider=decisions,
        clock=FixedClock(NOW),
        paper_mode=PaperMode.REALISTIC_PAPER,
    )

    cycle = runtime.run_cycle(
        ["TEST"]
    )

    result = cycle.results["TEST"]

    assert (
        result.status
        is RuntimeAssetStatus.FILLED
    )

    assert (
        result.broker_result.status
        is OrderStatus.FILLED
    )

    assert (
        runtime.positions["TEST"].status
        is PositionStatus.OPEN
    )

    assert (
        result.broker_result.execution.reference_price
        == 101.0
    )


def test_runtime_does_not_open_second_position():
    data = FakeMarketDataService(
        snapshots={
            "TEST": snapshot("TEST"),
        }
    )

    decisions = QueueDecisionProvider(
        [
            entry_decision(),
            entry_decision(),
        ]
    )

    runtime = RealisticPaperRuntime(
        market_data_service=data,
        market_session_service=FakeSessionService(),
        broker=make_broker(),
        decision_provider=decisions,
        clock=FixedClock(NOW),
    )

    first = runtime.run_cycle(
        ["TEST"]
    )

    second = runtime.run_cycle(
        ["TEST"]
    )

    assert (
        first.results["TEST"].status
        is RuntimeAssetStatus.FILLED
    )

    assert (
        second.results["TEST"].status
        is RuntimeAssetStatus.POSITION_ALREADY_OPEN
    )

    assert len(runtime.positions) == 1


def test_runtime_closes_tracked_position():
    data = FakeMarketDataService(
        snapshots={
            "TEST": snapshot("TEST"),
        }
    )

    decisions = QueueDecisionProvider(
        [
            entry_decision(),
            exit_decision(),
        ]
    )

    runtime = RealisticPaperRuntime(
        market_data_service=data,
        market_session_service=FakeSessionService(),
        broker=make_broker(),
        decision_provider=decisions,
        clock=FixedClock(NOW),
    )

    runtime.run_cycle(
        ["TEST"]
    )

    cycle = runtime.run_cycle(
        ["TEST"]
    )

    result = cycle.results["TEST"]

    assert (
        result.status
        is RuntimeAssetStatus.FILLED
    )

    assert "TEST" not in runtime.positions

    assert (
        result.broker_result.position.status
        is PositionStatus.CLOSED
    )

    assert (
        result.broker_result.execution.execution_reason
        == "TIME_EXIT"
    )


def test_runtime_exit_without_position_is_not_submitted():
    runtime = RealisticPaperRuntime(
        market_data_service=FakeMarketDataService(
            snapshots={
                "TEST": snapshot("TEST"),
            }
        ),
        market_session_service=FakeSessionService(),
        broker=make_broker(),
        decision_provider=QueueDecisionProvider(
            [
                exit_decision(),
            ]
        ),
        clock=FixedClock(NOW),
    )

    cycle = runtime.run_cycle(
        ["TEST"]
    )

    assert (
        cycle.results["TEST"].status
        is RuntimeAssetStatus.NO_POSITION
    )


def test_runtime_isolates_market_data_error():
    runtime = RealisticPaperRuntime(
        market_data_service=FakeMarketDataService(
            snapshots={
                "GOOD": snapshot("GOOD"),
            },
            errors={
                "BAD": "PROVIDER_TIMEOUT",
            },
        ),
        market_session_service=FakeSessionService(),
        broker=make_broker(),
        decision_provider=lambda **kwargs: (
            entry_decision()
        ),
        clock=FixedClock(NOW),
    )

    cycle = runtime.run_cycle(
        [
            "GOOD",
            "BAD",
        ]
    )

    assert (
        cycle.results["GOOD"].status
        is RuntimeAssetStatus.FILLED
    )

    assert (
        cycle.results["BAD"].status
        is RuntimeAssetStatus.DATA_ERROR
    )

    assert (
        cycle.results["BAD"].error
        == "PROVIDER_TIMEOUT"
    )


def test_runtime_isolates_session_error():
    runtime = RealisticPaperRuntime(
        market_data_service=FakeMarketDataService(
            snapshots={
                "GOOD": snapshot("GOOD"),
                "BAD": snapshot("BAD"),
            }
        ),
        market_session_service=FakeSessionService(
            fail_assets={"BAD"}
        ),
        broker=make_broker(),
        decision_provider=lambda **kwargs: (
            entry_decision()
        ),
        clock=FixedClock(NOW),
    )

    cycle = runtime.run_cycle(
        [
            "GOOD",
            "BAD",
        ]
    )

    assert (
        cycle.results["GOOD"].status
        is RuntimeAssetStatus.FILLED
    )

    assert (
        cycle.results["BAD"].status
        is RuntimeAssetStatus.SESSION_ERROR
    )

    assert (
        "session unavailable"
        in cycle.results["BAD"].error
    )


def test_runtime_none_decision_is_hold():
    runtime = RealisticPaperRuntime(
        market_data_service=FakeMarketDataService(
            snapshots={
                "TEST": snapshot("TEST"),
            }
        ),
        market_session_service=FakeSessionService(),
        broker=make_broker(),
        decision_provider=lambda **kwargs: None,
        clock=FixedClock(NOW),
    )

    cycle = runtime.run_cycle(
        ["TEST"]
    )

    assert (
        cycle.results["TEST"].status
        is RuntimeAssetStatus.HOLD
    )


def test_runtime_preserves_market_closed_rejection():
    runtime = RealisticPaperRuntime(
        market_data_service=FakeMarketDataService(
            snapshots={
                "TEST": snapshot("TEST"),
            }
        ),
        market_session_service=FakeSessionService(
            state=SessionState.CLOSED
        ),
        broker=make_broker(),
        decision_provider=lambda **kwargs: (
            entry_decision()
        ),
        clock=FixedClock(NOW),
    )

    cycle = runtime.run_cycle(
        ["TEST"]
    )

    result = cycle.results["TEST"]

    assert (
        result.status
        is RuntimeAssetStatus.REJECTED
    )

    assert (
        result.broker_result.status
        is OrderStatus.REJECTED
    )


def test_runtime_order_is_always_realistic_v2():
    runtime = RealisticPaperRuntime(
        market_data_service=FakeMarketDataService(
            snapshots={
                "TEST": snapshot("TEST"),
            }
        ),
        market_session_service=FakeSessionService(),
        broker=make_broker(),
        decision_provider=lambda **kwargs: (
            entry_decision()
        ),
        clock=FixedClock(NOW),
    )

    cycle = runtime.run_cycle(
        ["TEST"]
    )

    order = (
        cycle.results["TEST"]
        .broker_result
        .order
    )

    assert (
        order.execution_profile.value
        == "REALISTIC_V2"
    )

    assert (
        order.paper_mode
        is PaperMode.REALISTIC_PAPER
    )
