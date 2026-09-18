from datetime import date, datetime, timezone
from decimal import Decimal
from types import MappingProxyType, SimpleNamespace

import pytest

from src.accounting.runtime_bridge import (
    Phase09RuntimeAccountingBridge,
)
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
    PaperMode,
    PositionStatus,
)
from src.execution.paper_broker import (
    PaperBroker,
)
from src.execution.runtime import (
    ExecutionDecision,
    RuntimeAssetStatus,
)
from src.execution.slippage import (
    FixedBpsSlippage,
)
from src.fx.models import (
    FxQuote,
    FxSourceQuality,
)
from src.fx.realized_booking import (
    RealizedFxBooker,
)
from src.fx.realized_selection import (
    RealizedFxSelectionPolicy,
)
from src.market.market_session import (
    MarketSessionSnapshot,
    SessionQuality,
    SessionState,
)
from src.persistence.sqlite_accounting_authority import (
    SQLiteCashAuthority,
)
from src.persistence.sqlite_bootstrap import (
    bootstrap_fresh_database,
)
from src.persistence.sqlite_injected_runtime import (
    InjectedCycleWrite,
    SQLiteInjectedRuntime,
)
from src.persistence.sqlite_realistic_v2_mapper import (
    RealisticV2SQLiteMapper,
)
from src.persistence.sqlite_repository import (
    SQLiteLedgerRepository,
)
from src.persistence.sqlite_runtime_bundle import (
    build_sqlite_only_runtime_bundle,
)


UTC = timezone.utc

ENTRY_AT = datetime(
    2026,
    9,
    19,
    0,
    40,
    tzinfo=UTC,
)

EXIT_AT = datetime(
    2026,
    9,
    19,
    0,
    50,
    tzinfo=UTC,
)

ENTRY_TEXT = "2026-09-19T00:40:00Z"
EXIT_TEXT = "2026-09-19T00:50:00Z"


class FakeAsset:
    asset_id = "AAPL"
    allow_long = True
    allow_short = False
    short_mechanism = "NONE"
    short_financing_model = None


def asset_resolver(asset_id):
    assert asset_id == "AAPL"
    return FakeAsset()


def seed_restart_database(path):
    bootstrap_fresh_database(
        path,
        initial_cash_pln="1000",
        bootstrap_id="phase13-a20",
        created_at_utc=ENTRY_TEXT,
    )

    repo = SQLiteLedgerRepository.open_writer(
        path
    )

    try:
        with repo.atomic_cycle():
            repo.clear_halt_explicitly(
                reason="A20 temporary activation",
                updated_at_utc=ENTRY_TEXT,
                event_id="a20-clear",
                event_timestamp_utc=ENTRY_TEXT,
            )

            repo.insert_order_idempotent(
                {
                    "order_id": "order-entry-a20",
                    "client_order_id": "client-entry-a20",
                    "asset_id": "AAPL",
                    "strategy_id": "PHASE13_A20",
                    "intent": "ENTRY",
                    "side": "BUY",
                    "quantity_native": "2",
                    "signal_reference": "A20_ENTRY",
                    "source_timestamp_utc": ENTRY_TEXT,
                    "created_at_utc": ENTRY_TEXT,
                    "execution_profile": "REALISTIC_V2",
                    "paper_mode": "realistic_paper",
                    "status": "FILLED",
                    "config_hash": "a" * 64,
                    "order_fingerprint": "fingerprint-entry-a20",
                    "raw_json": {"phase": "13A20"},
                }
            )

            repo.insert_execution_idempotent(
                {
                    "execution_id": "execution-entry-a20",
                    "order_id": "order-entry-a20",
                    "asset_id": "AAPL",
                    "side": "BUY",
                    "quantity_native": "2",
                    "reference_price_native": "100",
                    "execution_price_native": "100",
                    "bid_native": "100",
                    "ask_native": "100",
                    "spread_native": "0",
                    "slippage_native": "0",
                    "fee_native": "0.2",
                    "fee_pln": "0.8",
                    "provider_timestamp_utc": ENTRY_TEXT,
                    "execution_timestamp_utc": ENTRY_TEXT,
                    "data_quality": "REALTIME",
                    "execution_quality": "REAL_BOOK",
                    "session_quality": "EXCHANGE_CALENDAR",
                    "fx_path": "USD->PLN",
                    "fx_rate": "4",
                    "fx_provider": "NBP_TABLE_A",
                    "fx_timestamp_utc": ENTRY_TEXT,
                    "fx_quality": "DAILY_REFERENCE",
                    "config_hash": "a" * 64,
                    "raw_json": {"phase": "13A20"},
                }
            )

            repo.save_position_idempotent(
                {
                    "position_id": "position-a20",
                    "asset_id": "AAPL",
                    "side": "LONG",
                    "quantity_native": "2",
                    "entry_execution_id": "execution-entry-a20",
                    "exit_execution_id": None,
                    "entry_price_native": "100",
                    "exit_price_native": None,
                    "stop_loss_native": "95",
                    "take_profit_native": "120",
                    "status": "OPEN",
                    "opened_at_utc": ENTRY_TEXT,
                    "closed_at_utc": None,
                    "short_mechanism": None,
                    "short_financing_model": None,
                    "execution_profile": "REALISTIC_V2",
                    "execution_quality_at_entry": "REAL_BOOK",
                    "unrealized_pnl_native": "0",
                    "unrealized_pnl_pln": "0",
                    "raw_json": {"phase": "13A20"},
                }
            )

            repo.set_last_processed_timestamp(
                processed_timestamp_utc=ENTRY_TEXT,
                updated_at_utc=ENTRY_TEXT,
            )

            repo.set_halt(
                reason="A20_TEST_HALT",
                updated_at_utc=ENTRY_TEXT,
                event_id="a20-halt",
                event_timestamp_utc=ENTRY_TEXT,
            )
    finally:
        repo.close()


def market_snapshot():
    return MarketSnapshot(
        asset_id="AAPL",
        bid=110.0,
        ask=110.0,
        last=110.0,
        provider_timestamp=EXIT_AT,
        received_at=EXIT_AT,
        data_quality=DataQuality.REALTIME,
        delayed=False,
        quote_age_seconds=0.0,
        provider_status=ProviderStatus.CONNECTED,
        execution_quality=ExecutionQuality.REAL_BOOK,
    )


class FakeMarketDataService:
    def __init__(self):
        self.calls = []

    def run_cycle(self, asset_ids):
        self.calls.append(
            tuple(asset_ids)
        )

        return SimpleNamespace(
            snapshots=MappingProxyType(
                {
                    "AAPL": market_snapshot(),
                }
            ),
            errors=MappingProxyType({}),
            duration_seconds=0.1,
            timed_out=False,
        )


def market_session():
    return MarketSessionSnapshot(
        asset_id="AAPL",
        session_id="NASDAQ",
        state=SessionState.OPEN,
        session_quality=SessionQuality.EXCHANGE_CALENDAR,
        observed_at=EXIT_AT,
        timezone_name="America/New_York",
        local_time=EXIT_AT,
        reason="A20_TEST",
        calendar_version="a20",
    )


class FakeMarketSessionService:
    def get_session(
        self,
        asset_id,
        at,
    ):
        assert asset_id == "AAPL"
        return market_session()


class ExitDecisionProvider:
    def __init__(self):
        self.calls = 0

    def __call__(
        self,
        *,
        asset_id,
        snapshot,
        position,
    ):
        self.calls += 1

        assert asset_id == "AAPL"
        assert position is not None

        return ExecutionDecision(
            side=OrderSide.SELL,
            intent=OrderIntent.EXIT,
            quantity=2.0,
            exit_reason="TIME_EXIT",
            signal_reference="A20_EXIT",
        )


class EntryDecisionProvider:
    def __init__(self):
        self.calls = 0

    def __call__(
        self,
        *,
        asset_id,
        snapshot,
        position,
    ):
        self.calls += 1

        return ExecutionDecision(
            side=OrderSide.BUY,
            intent=OrderIntent.ENTRY,
            quantity=2.0,
            stop_loss=95.0,
            take_profit=120.0,
            signal_reference="A20_DUP_ENTRY",
        )


def broker():
    return PaperBroker(
        clock=FixedClock(EXIT_AT),
        asset_resolver=asset_resolver,
        slippage_model=FixedBpsSlippage(0.0),
        trading_fee_rate=0.001,
        execution_journal=None,
    )


def accounting_bridge():
    return Phase09RuntimeAccountingBridge(
        fx_enabled=True,
        pln_accounting_enabled=True,
        realized_fx_selection_policy=(
            RealizedFxSelectionPolicy(
                market_max_age_seconds=7200,
                daily_reference_max_age_days=7,
            )
        ),
        realized_fx_booker=(
            RealizedFxBooker(
                clock=FixedClock(
                    EXIT_AT
                )
            )
        ),
    )


def fx_quote():
    return FxQuote(
        base_currency="USD",
        quote_currency="PLN",
        rate=4.0,
        provider="NBP_TABLE_A",
        provider_timestamp=None,
        observed_at=EXIT_AT,
        source_quality=FxSourceQuality.DAILY_REFERENCE,
        table="181/A/NBP/2026",
        effective_date=date(
            2026,
            9,
            18,
        ),
    )


def mapper(repo, broker_value):
    def execution_evidence(
        *,
        execution,
        intent,
        realized_result,
    ):
        fee_pln = (
            Decimal(
                str(
                    execution.fee
                )
            )
            * Decimal("4")
        )

        return {
            "fee_pln": str(fee_pln),
            "fx_path": "USD->PLN",
            "fx_rate": "4",
            "fx_provider": "NBP_TABLE_A",
            "fx_timestamp_utc": EXIT_AT,
            "fx_quality": "DAILY_REFERENCE",
        }

    def realized_evidence(
        *,
        asset_id,
        position,
        execution,
        realized_result,
    ):
        entry = repo.connection.execute(
            """
            SELECT fee_pln
            FROM executions
            WHERE execution_id = ?
            """,
            (
                position.entry_execution_id,
            ),
        ).fetchone()

        assert entry is not None

        exit_fee_pln = (
            Decimal(
                str(
                    execution.fee
                )
            )
            * Decimal("4")
        )

        total_fees = (
            Decimal(
                str(
                    entry["fee_pln"]
                )
            )
            + exit_fee_pln
        )

        return {
            "fees_pln": str(total_fees),
            "spread_cost_pln": "0",
            "slippage_pln": "0",
            "fx_pair": "USDPLN",
            "fx_provider": "NBP_TABLE_A",
            "fx_timestamp_utc": EXIT_AT,
            "fx_quality": "DAILY_REFERENCE",
        }

    return RealisticV2SQLiteMapper(
        order_fingerprint_resolver=(
            broker_value.order_fingerprint
        ),
        execution_evidence_resolver=(
            execution_evidence
        ),
        realized_evidence_resolver=(
            realized_evidence
        ),
        strategy_id="PHASE13_A20",
    )


def build_bundle(
    *,
    path,
    live_path,
    decision_provider,
):
    broker_value = broker()
    repo_for_mapper = (
        SQLiteLedgerRepository.open_writer(
            path
        )
    )

    # Close this probe immediately. The real bundle must own the only
    # writer during runtime execution.
    repo_for_mapper.close()

    def mapper_factory(repository):
        return mapper(
            repository,
            broker_value,
        )

    return build_sqlite_only_runtime_bundle(
        database_path=path,
        live_database_path=live_path,
        market_data_service=FakeMarketDataService(),
        market_session_service=FakeMarketSessionService(),
        broker=broker_value,
        decision_provider=decision_provider,
        clock=FixedClock(EXIT_AT),
        paper_mode=PaperMode.REALISTIC_PAPER,
        accounting_bridge=accounting_bridge(),
        fx_conversion_resolver=(
            lambda **kwargs: None
        ),
        estimated_exit_fee_resolver=(
            lambda **kwargs: 0
        ),
        realized_quotes_resolver=(
            lambda **kwargs: (
                fx_quote(),
            )
        ),
        cycle_mapper_factory=mapper_factory,
    )


def test_external_repository_injection_does_not_close_owner_repo(
    tmp_path,
):
    path = tmp_path / "a20-owner.db"

    bootstrap_fresh_database(
        path,
        initial_cash_pln="1000",
        bootstrap_id="a20-owner",
        created_at_utc=ENTRY_TEXT,
    )

    repo = SQLiteLedgerRepository.open_writer(
        path
    )

    class FakeRuntime:
        def run_cycle(
            self,
            asset_ids,
        ):
            return object()

    wrapper = SQLiteInjectedRuntime(
        runtime=FakeRuntime(),
        database_path=path,
        live_database_path=tmp_path / "live.db",
        repository=repo,
        cycle_mapper=(
            lambda **kwargs: InjectedCycleWrite(
                intent="NOOP",
                processed_timestamp_utc=None,
                updated_at_utc=None,
            )
        ),
        snapshot_provider=lambda: None,
        restore_snapshot=lambda value: None,
    )

    wrapper.close()

    # External owner still has a valid connection.
    assert (
        repo.connection.execute(
            "SELECT 1"
        ).fetchone()[0]
        == 1
    )

    repo.close()


def test_complete_sqlite_only_bundle_executes_actual_exit_after_restart(
    tmp_path,
):
    path = tmp_path / "a20.db"
    live_path = tmp_path / "forbidden-live.db"

    seed_restart_database(
        path
    )

    decision = ExitDecisionProvider()

    bundle = build_bundle(
        path=path,
        live_path=live_path,
        decision_provider=decision,
    )

    try:
        assert (
            bundle.injected_runtime.repository
            is bundle.repository
        )
        assert "AAPL" in bundle.base_runtime.positions

        state_before = (
            bundle.repository
            .read_system_state()
        )

        assert state_before["halted"] == 1
        assert state_before["halt_reason"] == "A20_TEST_HALT"
        assert (
            SQLiteCashAuthority(
                bundle.repository
            ).current_cash_pln()
            == Decimal("1000")
        )

        result = bundle.run_cycle(
            ["AAPL"]
        )

        assert result.persisted is True
        assert result.blocked_by_halt is False
        assert decision.calls == 1

        accounting_result = result.runtime_result

        execution_result = (
            accounting_result
            .execution_cycle
            .results["AAPL"]
        )

        assert (
            execution_result.status
            is RuntimeAssetStatus.FILLED
        )

        realized = (
            accounting_result
            .accounting_results["AAPL"]
            .realized_result
        )

        assert realized is not None
        assert (
            realized
            .accounting_record
            .net_realized_pnl_native
            == Decimal("19.58")
        )
        assert (
            realized
            .accounting_record
            .net_realized_pnl_pln
            == Decimal("78.320")
        )

        repo = bundle.repository

        assert repo.count_rows("orders") == 2
        assert repo.count_rows("executions") == 2
        assert repo.count_rows("trades") == 1

        position = repo.connection.execute(
            """
            SELECT *
            FROM positions
            WHERE position_id = ?
            """,
            ("position-a20",),
        ).fetchone()

        assert position["status"] == "CLOSED"
        assert position["exit_execution_id"] is not None

        assert (
            SQLiteCashAuthority(
                repo
            ).current_cash_pln()
            == Decimal("1078.320")
        )

        state_after = repo.read_system_state()

        assert state_after["halted"] == 1
        assert state_after["halt_reason"] == "A20_TEST_HALT"

        assert repo.reconcile_cash().matches is True
        assert (
            repo.reconcile_realized_pnl()[
                "matches"
            ]
            is True
        )

        assert "AAPL" not in bundle.base_runtime.positions

        assert not list(
            tmp_path.rglob("*.json")
        )
        assert not list(
            tmp_path.rglob("*.jsonl")
        )
    finally:
        bundle.close()


def test_restart_after_close_restores_no_position_and_halt_blocks_entry(
    tmp_path,
):
    path = tmp_path / "a20.db"
    live_path = tmp_path / "forbidden-live.db"

    seed_restart_database(
        path
    )

    first = build_bundle(
        path=path,
        live_path=live_path,
        decision_provider=ExitDecisionProvider(),
    )

    first.run_cycle(
        ["AAPL"]
    )
    first.close()

    entry_decision = EntryDecisionProvider()

    second = build_bundle(
        path=path,
        live_path=live_path,
        decision_provider=entry_decision,
    )

    try:
        assert "AAPL" not in second.base_runtime.positions

        result = second.run_cycle(
            ["AAPL"]
        )

        assert result.persisted is False
        assert result.blocked_by_halt is True
        assert result.runtime_result is None
        assert entry_decision.calls == 0

        assert (
            SQLiteCashAuthority(
                second.repository
            ).current_cash_pln()
            == Decimal("1078.320")
        )
        assert second.repository.count_rows("orders") == 2
        assert second.repository.count_rows("trades") == 1
    finally:
        second.close()


def test_bundle_rejects_live_database_path_before_open(tmp_path):
    path = tmp_path / "same.db"

    seed_restart_database(
        path
    )

    with pytest.raises(
        Exception,
        match="live",
    ):
        build_sqlite_only_runtime_bundle(
            database_path=path,
            live_database_path=path,
            market_data_service=FakeMarketDataService(),
            market_session_service=FakeMarketSessionService(),
            broker=broker(),
            decision_provider=ExitDecisionProvider(),
            clock=FixedClock(EXIT_AT),
            paper_mode=PaperMode.REALISTIC_PAPER,
            accounting_bridge=accounting_bridge(),
            fx_conversion_resolver=lambda **kwargs: None,
            estimated_exit_fee_resolver=lambda **kwargs: 0,
            realized_quotes_resolver=lambda **kwargs: (fx_quote(),),
            cycle_mapper_factory=lambda repository: mapper(
                repository,
                broker(),
            ),
        )
