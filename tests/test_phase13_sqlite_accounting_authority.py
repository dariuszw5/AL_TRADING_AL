from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest

from src.accounting.runtime_bridge import (
    Phase09RuntimeAccountingBridge,
    RuntimeAccountingBridgeError,
)
from src.accounting.runtime_integration import (
    SnapshotCaptureDecisionProvider,
)
from src.core.clock import FixedClock
from src.data.market_data import (
    ExecutionQuality,
)
from src.execution.models import (
    Execution,
    ExecutionProfile,
    Order,
    OrderIntent,
    OrderSide,
    OrderStatus,
    PaperMode,
    PositionSide,
    PositionStatus,
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
from src.persistence.sqlite_accounting_authority import (
    SQLiteAccountingAuthorityError,
    SQLiteCashAuthority,
    build_sqlite_phase09_accounting_runtime,
)
from src.persistence.sqlite_bootstrap import (
    bootstrap_fresh_database,
)
from src.persistence.sqlite_only_runtime import (
    SQLiteOpenPositionLoader,
)
from src.persistence.sqlite_realistic_v2_mapper import (
    RealisticV2SQLiteMapper,
)
from src.persistence.sqlite_repository import (
    SQLiteLedgerRepository,
)
from src.persistence.sqlite_trade_cycle import (
    SQLiteTradeCycleCoordinator,
)


UTC = timezone.utc

ENTRY_AT = datetime(
    2026,
    9,
    19,
    0,
    10,
    tzinfo=UTC,
)

EXIT_AT = datetime(
    2026,
    9,
    19,
    0,
    20,
    tzinfo=UTC,
)

ENTRY_TEXT = "2026-09-19T00:10:00Z"
EXIT_TEXT = "2026-09-19T00:20:00Z"


def seed_restart_database(path):
    bootstrap_fresh_database(
        path,
        initial_cash_pln="1000",
        bootstrap_id="phase13-a19",
        created_at_utc=ENTRY_TEXT,
    )

    repo = SQLiteLedgerRepository.open_writer(
        path
    )

    with repo.atomic_cycle():
        repo.clear_halt_explicitly(
            reason="A19 temporary activation",
            updated_at_utc=ENTRY_TEXT,
            event_id="a19-clear",
            event_timestamp_utc=ENTRY_TEXT,
        )

        repo.insert_order_idempotent(
            {
                "order_id": "order-entry-a19",
                "client_order_id": "client-entry-a19",
                "asset_id": "AAPL",
                "strategy_id": "PHASE13_A19",
                "intent": "ENTRY",
                "side": "BUY",
                "quantity_native": "2",
                "signal_reference": "A19_ENTRY",
                "source_timestamp_utc": ENTRY_TEXT,
                "created_at_utc": ENTRY_TEXT,
                "execution_profile": "REALISTIC_V2",
                "paper_mode": "realistic_paper",
                "status": "FILLED",
                "config_hash": "a" * 64,
                "order_fingerprint": "fingerprint-entry-a19",
                "raw_json": {"phase": "13A19"},
            }
        )

        repo.insert_execution_idempotent(
            {
                "execution_id": "execution-entry-a19",
                "order_id": "order-entry-a19",
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
                "raw_json": {"phase": "13A19"},
            }
        )

        repo.save_position_idempotent(
            {
                "position_id": "position-a19",
                "asset_id": "AAPL",
                "side": "LONG",
                "quantity_native": "2",
                "entry_execution_id": "execution-entry-a19",
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
                "raw_json": {"phase": "13A19"},
            }
        )

        repo.set_last_processed_timestamp(
            processed_timestamp_utc=ENTRY_TEXT,
            updated_at_utc=ENTRY_TEXT,
        )

    return repo


def fx_quote():
    return FxQuote(
        base_currency="USD",
        quote_currency="PLN",
        rate=4.0,
        provider="NBP_TABLE_A",
        provider_timestamp=None,
        observed_at=EXIT_AT,
        source_quality=(
            FxSourceQuality.DAILY_REFERENCE
        ),
        table="181/A/NBP/2026",
        effective_date=date(
            2026,
            9,
            18,
        ),
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


def build_accounting_runtime(repo):
    capture = SnapshotCaptureDecisionProvider(
        lambda **kwargs: None
    )

    runtime = SimpleNamespace(
        decision_provider=capture,
        positions={},
    )

    return build_sqlite_phase09_accounting_runtime(
        repository=repo,
        runtime=runtime,
        accounting_bridge=accounting_bridge(),
        snapshot_capture=capture,
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
    )


def closed_position(open_position):
    return SimpleNamespace(
        position_id=open_position.position_id,
        asset_id=open_position.asset_id,
        side=open_position.side,
        quantity=open_position.quantity,
        entry_execution_id=(
            open_position.entry_execution_id
        ),
        entry_price=open_position.entry_price,
        stop_loss=open_position.stop_loss,
        take_profit=open_position.take_profit,
        opened_at=open_position.opened_at,
        short_mechanism=(
            open_position.short_mechanism
        ),
        short_financing_model=(
            open_position.short_financing_model
        ),
        execution_profile=(
            open_position.execution_profile
        ),
        execution_quality_at_entry=(
            open_position
            .execution_quality_at_entry
        ),
        status=PositionStatus.CLOSED,
        closed_at=EXIT_AT,
        exit_execution_id="execution-exit-a19",
        exit_price=110.0,
        pending_exit_reason=None,
        pending_since=None,
    )


def exit_order():
    return Order(
        order_id="order-exit-a19",
        client_order_id="client-exit-a19",
        asset_id="AAPL",
        side=OrderSide.SELL,
        quantity=2.0,
        intent=OrderIntent.EXIT,
        created_at=EXIT_AT,
        execution_profile=(
            ExecutionProfile.REALISTIC_V2
        ),
        paper_mode=(
            PaperMode.REALISTIC_PAPER
        ),
        signal_reference="A19_EXIT",
        stop_loss=None,
        take_profit=None,
    )


def exit_execution():
    return Execution(
        execution_id="execution-exit-a19",
        order_id="order-exit-a19",
        asset_id="AAPL",
        side=OrderSide.SELL,
        quantity=2.0,
        reference_price=110.0,
        execution_price=110.0,
        bid=110.0,
        ask=110.0,
        spread=0.0,
        slippage=0.0,
        fee=0.22,
        provider_timestamp=EXIT_AT,
        execution_timestamp=EXIT_AT,
        data_quality="REALTIME",
        execution_quality=(
            ExecutionQuality.REAL_BOOK
        ),
        session_quality="EXCHANGE_CALENDAR",
        paper_mode=(
            PaperMode.REALISTIC_PAPER
        ),
        short_label=None,
        trigger_reason=None,
        pending_reason=None,
        execution_reason="FILLED",
        labels=(),
        config_hash="b" * 64,
    )


def execution_evidence(
    *,
    execution,
    intent,
    realized_result,
):
    return {
        "fee_pln": "0.88",
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
    return {
        "fees_pln": "1.68",
        "spread_cost_pln": "0",
        "slippage_pln": "0",
        "fx_pair": "USDPLN",
        "fx_provider": "NBP_TABLE_A",
        "fx_timestamp_utc": EXIT_AT,
        "fx_quality": "DAILY_REFERENCE",
    }


def runtime_result(
    *,
    position,
    realized_result,
):
    broker_result = SimpleNamespace(
        status=OrderStatus.FILLED,
        order=exit_order(),
        execution=exit_execution(),
        position=position,
    )

    return SimpleNamespace(
        execution_cycle=SimpleNamespace(
            results={
                "AAPL": SimpleNamespace(
                    status=OrderStatus.FILLED,
                    broker_result=broker_result,
                ),
            }
        ),
        accounting_results={
            "AAPL": SimpleNamespace(
                error=None,
                limitations=(),
                mtm_record=None,
                realized_result=realized_result,
            ),
        },
        limitations=(),
    )


def mapper():
    return RealisticV2SQLiteMapper(
        order_fingerprint_resolver=(
            lambda order: (
                "fingerprint-"
                + order.client_order_id
            )
        ),
        execution_evidence_resolver=(
            execution_evidence
        ),
        realized_evidence_resolver=(
            realized_evidence
        ),
        strategy_id="PHASE13_A19",
    )


def test_sqlite_cash_authority_reads_reconciled_cash(tmp_path):
    path = tmp_path / "a19.db"
    repo = seed_restart_database(path)

    try:
        authority = SQLiteCashAuthority(
            repo
        )

        assert (
            authority.current_cash_pln()
            == Decimal("1000")
        )
    finally:
        repo.close()


def test_sqlite_cash_authority_fails_on_mismatch(tmp_path):
    path = tmp_path / "a19.db"
    repo = seed_restart_database(path)

    try:
        with repo.atomic_cycle():
            repo.connection.execute(
                """
                UPDATE system_state
                SET cash_balance_pln = ?
                """,
                ("999",),
            )

        with pytest.raises(
            SQLiteAccountingAuthorityError,
            match="reconciliation",
        ):
            SQLiteCashAuthority(
                repo
            ).current_cash_pln()
    finally:
        repo.close()


def test_restart_accounting_uses_sqlite_entry_evidence(tmp_path):
    path = tmp_path / "a19.db"
    repo = seed_restart_database(path)
    repo.close()

    repo = SQLiteLedgerRepository.open_writer(
        path
    )

    try:
        open_position = (
            SQLiteOpenPositionLoader(
                repo
            )
            .load_positions()["AAPL"]
        )

        runtime = build_accounting_runtime(
            repo
        )

        assert runtime.entry_execution_ids == ()

        realized = runtime._book_realized(
            asset_id="AAPL",
            position=closed_position(
                open_position
            ),
            exit_execution=exit_execution(),
        )

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
        assert runtime.entry_execution_ids == ()

        assert (
            SQLiteCashAuthority(
                repo
            ).current_cash_pln()
            == Decimal("1000")
        )
    finally:
        repo.close()


def test_restart_accounting_missing_entry_fails_closed(tmp_path):
    path = tmp_path / "a19.db"
    repo = seed_restart_database(path)

    try:
        open_position = (
            SQLiteOpenPositionLoader(
                repo
            )
            .load_positions()["AAPL"]
        )

        broken = closed_position(
            open_position
        )
        broken.entry_execution_id = "missing-entry"

        runtime = build_accounting_runtime(
            repo
        )

        with pytest.raises(
            RuntimeAccountingBridgeError,
            match="ENTRY_EXECUTION_REQUIRED",
        ):
            runtime._book_realized(
                asset_id="AAPL",
                position=broken,
                exit_execution=exit_execution(),
            )
    finally:
        repo.close()


def test_accounting_result_settles_atomically_into_sqlite_cash_after_restart(
    tmp_path,
):
    path = tmp_path / "a19.db"
    repo = seed_restart_database(path)
    repo.close()

    repo = SQLiteLedgerRepository.open_writer(
        path
    )

    try:
        open_position = (
            SQLiteOpenPositionLoader(
                repo
            )
            .load_positions()["AAPL"]
        )
        closed = closed_position(
            open_position
        )

        accounting = build_accounting_runtime(
            repo
        )

        realized = accounting._book_realized(
            asset_id="AAPL",
            position=closed,
            exit_execution=exit_execution(),
        )

        write = mapper()(
            asset_id="AAPL",
            runtime_result=runtime_result(
                position=closed,
                realized_result=realized,
            ),
        )

        assert write.intent == "EXIT"
        assert (
            write.trade["realized_pnl_native"]
            == "19.58"
        )
        assert (
            write.trade["realized_pnl_pln"]
            == "78.320"
        )

        result = SQLiteTradeCycleCoordinator(
            repo
        ).persist_exit_and_settle_cycle(
            processed_timestamp_utc=(
                write.processed_timestamp_utc
            ),
            updated_at_utc=(
                write.updated_at_utc
            ),
            reconciliation_event_id=(
                write.reconciliation_event_id
            ),
            order=write.order,
            execution=write.execution,
            closed_position=write.position,
            trade=write.trade,
            portfolio_transaction=(
                write.portfolio_transaction
            ),
        )

        assert result.trade_created is True
        assert result.transaction_created is True
        assert (
            result.cash_balance_pln
            == Decimal("1078.320")
        )

        authority = SQLiteCashAuthority(
            repo
        )

        assert (
            authority.current_cash_pln()
            == Decimal("1078.320")
        )
        assert repo.reconcile_cash().matches is True
        assert (
            repo.reconcile_realized_pnl()[
                "matches"
            ]
            is True
        )

        row = repo.connection.execute(
            """
            SELECT status
            FROM positions
            WHERE position_id = ?
            """,
            ("position-a19",),
        ).fetchone()

        assert row["status"] == "CLOSED"

        replay = SQLiteTradeCycleCoordinator(
            repo
        ).persist_exit_and_settle_cycle(
            processed_timestamp_utc=(
                write.processed_timestamp_utc
            ),
            updated_at_utc=(
                write.updated_at_utc
            ),
            reconciliation_event_id=(
                write.reconciliation_event_id
            ),
            order=write.order,
            execution=write.execution,
            closed_position=write.position,
            trade=write.trade,
            portfolio_transaction=(
                write.portfolio_transaction
            ),
        )

        assert replay.trade_created is False
        assert replay.transaction_created is False
        assert (
            SQLiteCashAuthority(
                repo
            ).current_cash_pln()
            == Decimal("1078.320")
        )

        assert not list(
            tmp_path.rglob("*.json")
        )
        assert not list(
            tmp_path.rglob("*.jsonl")
        )
    finally:
        repo.close()
