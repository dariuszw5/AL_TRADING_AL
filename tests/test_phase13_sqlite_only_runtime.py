from datetime import datetime, timezone
from pathlib import Path

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
    PositionStatus,
)
from src.execution.paper_broker import (
    PaperBroker,
)
from src.execution.runtime import (
    ExecutionDecision,
    RealisticPaperRuntime,
    RuntimeAssetStatus,
)
from src.execution.slippage import (
    FixedBpsSlippage,
)
from src.market.market_session import (
    MarketSessionSnapshot,
    SessionQuality,
    SessionState,
)
from src.persistence.sqlite_bootstrap import (
    bootstrap_fresh_database,
)
from src.persistence.sqlite_only_runtime import (
    SQLiteEntryExecutionResolver,
    SQLiteOnlyRuntimeCompositionError,
    SQLiteOpenPositionLoader,
    VolatilePositionStateStore,
    assert_sqlite_only_components,
)
from src.persistence.sqlite_repository import (
    SQLiteLedgerRepository,
)


UTC = timezone.utc
NOW = datetime(
    2026,
    9,
    19,
    0,
    0,
    tzinfo=UTC,
)
NOW_TEXT = "2026-09-19T00:00:00Z"


def order_payload():
    return {
        "order_id": "order-entry-a18",
        "client_order_id": "client-entry-a18",
        "asset_id": "TEST",
        "strategy_id": "PHASE13_A18",
        "intent": "ENTRY",
        "side": "BUY",
        "quantity_native": "2",
        "signal_reference": "A18_RESTART",
        "source_timestamp_utc": NOW_TEXT,
        "created_at_utc": NOW_TEXT,
        "execution_profile": "REALISTIC_V2",
        "paper_mode": "realistic_paper",
        "status": "FILLED",
        "config_hash": "a" * 64,
        "order_fingerprint": "fingerprint-a18",
        "raw_json": {"phase": "13A18"},
    }


def execution_payload():
    return {
        "execution_id": "execution-entry-a18",
        "order_id": "order-entry-a18",
        "asset_id": "TEST",
        "side": "BUY",
        "quantity_native": "2",
        "reference_price_native": "100",
        "execution_price_native": "100",
        "bid_native": "99.9",
        "ask_native": "100",
        "spread_native": "0.1",
        "slippage_native": "0",
        "fee_native": "0.2",
        "fee_pln": "0.8",
        "provider_timestamp_utc": NOW_TEXT,
        "execution_timestamp_utc": NOW_TEXT,
        "data_quality": "REALTIME",
        "execution_quality": "REAL_BOOK",
        "session_quality": "EXCHANGE_CALENDAR",
        "fx_path": "USD->PLN",
        "fx_rate": "4",
        "fx_provider": "TEST",
        "fx_timestamp_utc": NOW_TEXT,
        "fx_quality": "LIVE",
        "config_hash": "a" * 64,
        "raw_json": {"phase": "13A18"},
    }


def position_payload():
    return {
        "position_id": "position-a18",
        "asset_id": "TEST",
        "side": "LONG",
        "quantity_native": "2",
        "entry_execution_id": "execution-entry-a18",
        "exit_execution_id": None,
        "entry_price_native": "100",
        "exit_price_native": None,
        "stop_loss_native": "95",
        "take_profit_native": "110",
        "status": "OPEN",
        "opened_at_utc": NOW_TEXT,
        "closed_at_utc": None,
        "short_mechanism": None,
        "short_financing_model": None,
        "execution_profile": "REALISTIC_V2",
        "execution_quality_at_entry": "REAL_BOOK",
        "unrealized_pnl_native": "0",
        "unrealized_pnl_pln": "0",
        "raw_json": {"phase": "13A18"},
    }


def seed_open_sqlite(path):
    bootstrap_fresh_database(
        path,
        initial_cash_pln="1000",
        bootstrap_id="phase13-a18",
        created_at_utc=NOW_TEXT,
    )

    repo = SQLiteLedgerRepository.open_writer(
        path
    )

    with repo.atomic_cycle():
        repo.clear_halt_explicitly(
            reason="A18 temp activation",
            updated_at_utc=NOW_TEXT,
            event_id="a18-clear",
            event_timestamp_utc=NOW_TEXT,
        )

        repo.insert_order_idempotent(
            order_payload()
        )
        repo.insert_execution_idempotent(
            execution_payload()
        )
        repo.save_position_idempotent(
            position_payload()
        )
        repo.set_last_processed_timestamp(
            processed_timestamp_utc=NOW_TEXT,
            updated_at_utc=NOW_TEXT,
        )

    return repo


def test_open_position_loader_restores_real_position(tmp_path):
    path = tmp_path / "a18.db"
    repo = seed_open_sqlite(path)

    try:
        restored = SQLiteOpenPositionLoader(
            repo
        ).load_positions()

        assert tuple(restored) == ("TEST",)

        position = restored["TEST"]

        assert position.position_id == "position-a18"
        assert position.asset_id == "TEST"
        assert position.status is PositionStatus.OPEN
        assert position.quantity == 2.0
        assert position.entry_execution_id == (
            "execution-entry-a18"
        )
        assert position.execution_profile is (
            ExecutionProfile.REALISTIC_V2
        )
        assert position.execution_quality_at_entry is (
            ExecutionQuality.REAL_BOOK
        )
    finally:
        repo.close()


def test_volatile_state_store_never_creates_files(tmp_path):
    path = tmp_path / "a18.db"
    repo = seed_open_sqlite(path)

    try:
        restored = SQLiteOpenPositionLoader(
            repo
        ).load_positions()

        before = {
            item.relative_to(tmp_path)
            for item in tmp_path.rglob("*")
            if item.is_file()
        }

        store = VolatilePositionStateStore(
            restored
        )

        assert store.load_positions() == restored
        assert not hasattr(store, "path")

        store.save_positions({})

        assert store.load_positions() == {}

        after = {
            item.relative_to(tmp_path)
            for item in tmp_path.rglob("*")
            if item.is_file()
        }

        assert after == before
        assert not list(
            tmp_path.rglob("*.json")
        )
        assert not list(
            tmp_path.rglob("*.jsonl")
        )
    finally:
        repo.close()


def test_sqlite_entry_execution_resolver_restores_financial_evidence(
    tmp_path,
):
    path = tmp_path / "a18.db"
    repo = seed_open_sqlite(path)

    try:
        position = (
            SQLiteOpenPositionLoader(
                repo
            )
            .load_positions()["TEST"]
        )

        execution = SQLiteEntryExecutionResolver(
            repo
        )(
            asset_id="TEST",
            position=position,
            entry_execution_id=(
                "execution-entry-a18"
            ),
        )

        assert execution is not None
        assert execution.execution_id == (
            "execution-entry-a18"
        )
        assert execution.order_id == "order-entry-a18"
        assert execution.asset_id == "TEST"
        assert execution.side is OrderSide.BUY
        assert execution.quantity == 2.0
        assert execution.reference_price == 100.0
        assert execution.execution_price == 100.0
        assert execution.bid == 99.9
        assert execution.ask == 100.0
        assert execution.spread == 0.1
        assert execution.slippage == 0.0
        assert execution.fee == 0.2
        assert execution.config_hash == "a" * 64
        assert execution.paper_mode is (
            PaperMode.REALISTIC_PAPER
        )
    finally:
        repo.close()


def test_sqlite_entry_execution_resolver_returns_none_for_missing_id(
    tmp_path,
):
    path = tmp_path / "a18.db"
    repo = seed_open_sqlite(path)

    try:
        position = (
            SQLiteOpenPositionLoader(
                repo
            )
            .load_positions()["TEST"]
        )

        result = SQLiteEntryExecutionResolver(
            repo
        )(
            asset_id="TEST",
            position=position,
            entry_execution_id="missing",
        )

        assert result is None
    finally:
        repo.close()


class FakeAsset:
    asset_id = "TEST"
    allow_long = True
    allow_short = False
    short_mechanism = "NONE"
    short_financing_model = None


def asset_resolver(asset_id):
    assert asset_id == "TEST"
    return FakeAsset()


def snapshot():
    return MarketSnapshot(
        asset_id="TEST",
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


class FakeMarketDataService:
    def run_cycle(self, asset_ids):
        from types import MappingProxyType, SimpleNamespace

        return SimpleNamespace(
            snapshots=MappingProxyType(
                {
                    "TEST": snapshot(),
                }
            ),
            errors=MappingProxyType({}),
            duration_seconds=0.1,
            timed_out=False,
        )


def session():
    return MarketSessionSnapshot(
        asset_id="TEST",
        session_id="TEST",
        state=SessionState.OPEN,
        session_quality=(
            SessionQuality.EXCHANGE_CALENDAR
        ),
        observed_at=NOW,
        timezone_name="UTC",
        local_time=NOW,
        reason="TEST",
        calendar_version="a18",
    )


class FakeSessionService:
    def get_session(
        self,
        asset_id,
        at,
    ):
        return session()


class EntryDecision:
    def __call__(
        self,
        *,
        asset_id,
        snapshot,
        position,
    ):
        return ExecutionDecision(
            side=OrderSide.BUY,
            intent=OrderIntent.ENTRY,
            quantity=2.0,
            stop_loss=95.0,
            take_profit=110.0,
            signal_reference="a18-entry",
        )


def make_broker():
    return PaperBroker(
        clock=FixedClock(NOW),
        asset_resolver=asset_resolver,
        slippage_model=FixedBpsSlippage(0.0),
        trading_fee_rate=0.0,
        execution_journal=None,
    )


def test_sqlite_only_components_reject_legacy_durable_writer(
    tmp_path,
):
    class LegacyStore:
        path = tmp_path / "state.json"

        def load_positions(self):
            return {}

        def save_positions(self, positions):
            pass

    class BrokerWithJournal:
        execution_journal = object()

    with pytest.raises(
        SQLiteOnlyRuntimeCompositionError,
        match="volatile",
    ):
        assert_sqlite_only_components(
            state_store=LegacyStore(),
            broker=make_broker(),
        )

    with pytest.raises(
        SQLiteOnlyRuntimeCompositionError,
        match="execution_journal",
    ):
        assert_sqlite_only_components(
            state_store=VolatilePositionStateStore(),
            broker=BrokerWithJournal(),
        )


def test_real_runtime_restart_uses_sqlite_state_without_json_writers(
    tmp_path,
):
    path = tmp_path / "a18.db"
    repo = seed_open_sqlite(path)

    try:
        restored = SQLiteOpenPositionLoader(
            repo
        ).load_positions()
    finally:
        repo.close()

    store = VolatilePositionStateStore(
        restored
    )
    broker = make_broker()

    assert_sqlite_only_components(
        state_store=store,
        broker=broker,
    )

    runtime = RealisticPaperRuntime(
        market_data_service=FakeMarketDataService(),
        market_session_service=FakeSessionService(),
        broker=broker,
        decision_provider=EntryDecision(),
        clock=FixedClock(NOW),
        paper_mode=PaperMode.REALISTIC_PAPER,
        state_store=store,
    )

    assert "TEST" in runtime.positions
    assert runtime.positions["TEST"].position_id == (
        "position-a18"
    )

    result = runtime.run_cycle(
        ["TEST"]
    )

    assert result.results["TEST"].status is (
        RuntimeAssetStatus.POSITION_ALREADY_OPEN
    )
    assert "TEST" in runtime.positions

    assert not list(
        tmp_path.rglob("*.json")
    )
    assert not list(
        tmp_path.rglob("*.jsonl")
    )


def test_guard_accepts_sqlite_only_components():
    store = VolatilePositionStateStore()
    broker = make_broker()

    assert (
        assert_sqlite_only_components(
            state_store=store,
            broker=broker,
        )
        is None
    )
