from datetime import datetime, timezone

import pytest

from src.core.clock import FixedClock
from src.data.market_data import (
    DataQuality,
    ExecutionQuality,
    MarketSnapshot,
    ProviderStatus,
)
from src.execution.models import (
    ExecutionProfile,
    OrderIntent,
    OrderSide,
    PaperMode,
    Position,
    PositionSide,
    PositionStatus,
)
from src.execution.paper_broker import PaperBroker
from src.execution.runtime import (
    ExecutionDecision,
    RealisticPaperRuntime,
    RuntimeAssetStatus,
)
from src.execution.slippage import (
    FixedBpsSlippage,
)
from src.execution.state_store import (
    RealisticPaperStateStore,
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


def make_position(
    *,
    asset_id="TEST",
    status=PositionStatus.OPEN,
):
    return Position(
        position_id=f"pos-{asset_id}",
        asset_id=asset_id,
        side=PositionSide.LONG,
        quantity=2.0,
        entry_execution_id=(
            f"exec-{asset_id}"
        ),
        entry_price=101.0,
        stop_loss=95.0,
        take_profit=110.0,
        opened_at=NOW,
        short_mechanism=None,
        short_financing_model=None,
        execution_profile=(
            ExecutionProfile.REALISTIC_V2
        ),
        execution_quality_at_entry=(
            ExecutionQuality.REAL_BOOK
        ),
        status=status,
    )


def test_state_store_missing_file_loads_empty(
    tmp_path,
):
    store = RealisticPaperStateStore(
        tmp_path / "state.json",
        clock=FixedClock(NOW),
    )

    assert store.load_positions() == {}


def test_state_store_round_trip_position(
    tmp_path,
):
    path = tmp_path / "state.json"

    store = RealisticPaperStateStore(
        path,
        clock=FixedClock(NOW),
    )

    original = make_position()

    store.save_positions(
        {
            "TEST": original,
        }
    )

    restored = (
        store.load_positions()
    )

    assert restored == {
        "TEST": original,
    }

    assert path.exists()


def test_state_store_rejects_wrong_schema(
    tmp_path,
):
    path = tmp_path / "state.json"

    path.write_text(
        """
        {
          "schema_version": 999,
          "execution_profile": "REALISTIC_V2",
          "updated_at": "2026-09-16T15:00:00Z",
          "positions": []
        }
        """,
        encoding="utf-8",
    )

    store = RealisticPaperStateStore(
        path,
        clock=FixedClock(NOW),
    )

    with pytest.raises(
        ValueError,
        match="schema",
    ):
        store.load_positions()


def test_state_store_rejects_legacy_profile(
    tmp_path,
):
    path = tmp_path / "state.json"

    path.write_text(
        """
        {
          "schema_version": 1,
          "execution_profile": "LEGACY_V1",
          "updated_at": "2026-09-16T15:00:00Z",
          "positions": []
        }
        """,
        encoding="utf-8",
    )

    store = RealisticPaperStateStore(
        path,
        clock=FixedClock(NOW),
    )

    with pytest.raises(
        ValueError,
        match="REALISTIC_V2",
    ):
        store.load_positions()


def test_state_store_atomic_write_leaves_no_temp(
    tmp_path,
):
    path = tmp_path / "state.json"

    store = RealisticPaperStateStore(
        path,
        clock=FixedClock(NOW),
    )

    store.save_positions(
        {
            "TEST": make_position(),
        }
    )

    leftovers = list(
        tmp_path.glob(
            ".state.json.*.tmp"
        )
    )

    assert leftovers == []


class FakeAsset:

    def __init__(self, asset_id):
        self.asset_id = asset_id
        self.allow_long = True
        self.allow_short = False
        self.short_mechanism = "NONE"
        self.short_financing_model = None


def asset_resolver(asset_id):
    return FakeAsset(
        asset_id
    )


def make_snapshot(
    asset_id="TEST",
):
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
        provider_status=(
            ProviderStatus.CONNECTED
        ),
        execution_quality=(
            ExecutionQuality.REAL_BOOK
        ),
    )


def make_session(
    asset_id="TEST",
):
    return MarketSessionSnapshot(
        asset_id=asset_id,
        session_id="TEST_SESSION",
        state=SessionState.OPEN,
        session_quality=(
            SessionQuality.EXCHANGE_CALENDAR
        ),
        observed_at=NOW,
        timezone_name="UTC",
        local_time=NOW,
        reason="TEST",
        calendar_version="test-v1",
    )


class FakeMarketDataService:

    def run_cycle(
        self,
        asset_ids,
    ):
        from types import (
            MappingProxyType,
            SimpleNamespace,
        )

        snapshots = {
            asset_id: make_snapshot(
                asset_id
            )
            for asset_id in asset_ids
        }

        return SimpleNamespace(
            snapshots=MappingProxyType(
                snapshots
            ),
            errors=MappingProxyType(
                {}
            ),
            duration_seconds=0.1,
            timed_out=False,
        )


class FakeSessionService:

    def get_session(
        self,
        asset_id,
        at,
    ):
        return make_session(
            asset_id
        )


class DecisionQueue:

    def __init__(
        self,
        decisions,
    ):
        self.decisions = list(
            decisions
        )

    def __call__(
        self,
        *,
        asset_id,
        snapshot,
        position,
    ):
        if not self.decisions:
            return None

        return self.decisions.pop(0)


def make_broker():
    return PaperBroker(
        clock=FixedClock(NOW),
        asset_resolver=asset_resolver,
        slippage_model=(
            FixedBpsSlippage(0.0)
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
        signal_reference=(
            "restart-entry"
        ),
    )


def exit_decision():
    return ExecutionDecision(
        side=OrderSide.SELL,
        intent=OrderIntent.EXIT,
        quantity=2.0,
        exit_reason="TIME_EXIT",
        signal_reference=(
            "restart-exit"
        ),
    )


def build_runtime(
    *,
    store,
    decisions,
):
    return RealisticPaperRuntime(
        market_data_service=(
            FakeMarketDataService()
        ),
        market_session_service=(
            FakeSessionService()
        ),
        broker=make_broker(),
        decision_provider=(
            DecisionQueue(
                decisions
            )
        ),
        clock=FixedClock(NOW),
        paper_mode=(
            PaperMode.REALISTIC_PAPER
        ),
        state_store=store,
    )


def test_runtime_persists_open_position_and_restores_after_restart(
    tmp_path,
):
    path = tmp_path / "runtime.json"

    store1 = RealisticPaperStateStore(
        path,
        clock=FixedClock(NOW),
    )

    runtime1 = build_runtime(
        store=store1,
        decisions=[
            entry_decision(),
        ],
    )

    first = runtime1.run_cycle(
        ["TEST"]
    )

    assert (
        first.results["TEST"].status
        is RuntimeAssetStatus.FILLED
    )

    assert "TEST" in runtime1.positions

    # Simulated process restart:
    store2 = RealisticPaperStateStore(
        path,
        clock=FixedClock(NOW),
    )

    runtime2 = build_runtime(
        store=store2,
        decisions=[
            entry_decision(),
        ],
    )

    assert "TEST" in runtime2.positions

    second = runtime2.run_cycle(
        ["TEST"]
    )

    assert (
        second.results["TEST"].status
        is RuntimeAssetStatus.POSITION_ALREADY_OPEN
    )

    assert len(
        runtime2.positions
    ) == 1


def test_runtime_persists_close_and_restart_has_no_position(
    tmp_path,
):
    path = tmp_path / "runtime.json"

    store1 = RealisticPaperStateStore(
        path,
        clock=FixedClock(NOW),
    )

    runtime1 = build_runtime(
        store=store1,
        decisions=[
            entry_decision(),
        ],
    )

    runtime1.run_cycle(
        ["TEST"]
    )

    store2 = RealisticPaperStateStore(
        path,
        clock=FixedClock(NOW),
    )

    runtime2 = build_runtime(
        store=store2,
        decisions=[
            exit_decision(),
        ],
    )

    closed = runtime2.run_cycle(
        ["TEST"]
    )

    assert (
        closed.results["TEST"].status
        is RuntimeAssetStatus.FILLED
    )

    assert "TEST" not in runtime2.positions

    store3 = RealisticPaperStateStore(
        path,
        clock=FixedClock(NOW),
    )

    runtime3 = build_runtime(
        store=store3,
        decisions=[],
    )

    assert runtime3.positions == {}
