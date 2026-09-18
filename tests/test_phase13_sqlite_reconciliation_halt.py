from decimal import Decimal

import pytest

from src.persistence.sqlite_repository import (
    ReconciliationMismatchError,
    SQLiteLedgerRepository,
)


NOW = "2026-09-18T16:00:00.000000Z"


def order_payload(
    order_id,
    client_order_id,
    side,
):
    return {
        "order_id": order_id,
        "client_order_id": client_order_id,
        "asset_id": "BTCUSDT",
        "strategy_id": "TEST",
        "intent": (
            "ENTRY"
            if side == "BUY"
            else "EXIT"
        ),
        "side": side,
        "quantity_native": "1",
        "signal_reference": "PHASE13_A4",
        "source_timestamp_utc": NOW,
        "created_at_utc": NOW,
        "execution_profile": "REALISTIC_V2",
        "paper_mode": "realistic_paper",
        "status": "FILLED",
        "config_hash": "config-a4",
        "order_fingerprint": (
            f"fingerprint-{order_id}"
        ),
        "raw_json": {
            "phase": "13A4",
        },
    }


def execution_payload(
    execution_id,
    order_id,
    side,
    price,
):
    return {
        "execution_id": execution_id,
        "order_id": order_id,
        "asset_id": "BTCUSDT",
        "side": side,
        "quantity_native": "1",
        "reference_price_native": price,
        "execution_price_native": price,
        "bid_native": price,
        "ask_native": price,
        "spread_native": "0",
        "slippage_native": "0",
        "fee_native": "0",
        "fee_pln": "0",
        "provider_timestamp_utc": NOW,
        "execution_timestamp_utc": NOW,
        "data_quality": "REALTIME_BOOK",
        "execution_quality": "REAL_BOOK",
        "session_quality": "EXCHANGE_CALENDAR",
        "fx_path": "USDT->USD->PLN",
        "fx_rate": "4",
        "fx_provider": "TEST",
        "fx_timestamp_utc": NOW,
        "fx_quality": "LIVE",
        "config_hash": "config-a4",
        "raw_json": {
            "phase": "13A4",
        },
    }


def transaction_payload(
    transaction_id,
    transaction_type,
    amount,
    reference_id,
):
    return {
        "transaction_id": transaction_id,
        "transaction_type": transaction_type,
        "amount_pln": amount,
        "asset_id": "BTCUSDT",
        "reference_type": "TRADE",
        "reference_id": reference_id,
        "booked_at_utc": NOW,
        "fx_pair": "USDPLN",
        "fx_path": "USDT->USD->PLN",
        "fx_rate": "4",
        "fx_provider": "TEST",
        "fx_timestamp_utc": NOW,
        "fx_quality": "LIVE",
        "raw_json": {
            "phase": "13A4",
        },
    }


def position_payload():
    return {
        "position_id": "position-1",
        "asset_id": "BTCUSDT",
        "side": "LONG",
        "quantity_native": "1",
        "entry_execution_id": "execution-entry",
        "exit_execution_id": "execution-exit",
        "entry_price_native": "100",
        "exit_price_native": "106.25",
        "stop_loss_native": "95",
        "take_profit_native": "110",
        "status": "CLOSED",
        "opened_at_utc": NOW,
        "closed_at_utc": NOW,
        "short_mechanism": None,
        "short_financing_model": None,
        "execution_profile": "REALISTIC_V2",
        "execution_quality_at_entry": "REAL_BOOK",
        "unrealized_pnl_native": "0",
        "unrealized_pnl_pln": "0",
        "raw_json": {
            "phase": "13A4",
        },
    }


def trade_payload(
    realized_pln="25",
):
    return {
        "trade_id": "trade-1",
        "asset_id": "BTCUSDT",
        "position_id": "position-1",
        "entry_execution_id": "execution-entry",
        "exit_execution_id": "execution-exit",
        "quantity_native": "1",
        "realized_pnl_native": "6.25",
        "realized_pnl_pln": realized_pln,
        "fees_pln": "0",
        "spread_cost_pln": "0",
        "slippage_pln": "0",
        "realized_fx_pair": "USDPLN",
        "realized_fx_path": "USDT->USD->PLN",
        "realized_fx_rate": "4",
        "realized_fx_provider": "TEST",
        "realized_fx_timestamp_utc": NOW,
        "realized_fx_quality": "LIVE",
        "realized_transaction_id": "txn-realized-1",
        "opened_at_utc": NOW,
        "closed_at_utc": NOW,
        "raw_json": {
            "phase": "13A4",
        },
    }


@pytest.fixture
def repository(tmp_path):
    path = tmp_path / "phase13_a4.db"

    repo = SQLiteLedgerRepository.open_writer(
        path,
    )

    repo.initialize_schema(
        applied_at_utc=NOW,
    )

    try:
        yield repo
    finally:
        repo.close()


def seed_closed_trade(
    repo,
    *,
    trade_realized_pln="25",
    ledger_realized_pln="25",
):
    with repo.atomic_cycle():
        repo.initialize_system_state(
            cash_balance_pln=(
                Decimal("1000")
                + Decimal(
                    ledger_realized_pln
                )
            ),
            updated_at_utc=NOW,
        )

        repo.append_portfolio_transaction_idempotent(
            transaction_payload(
                "txn-initial",
                "INITIAL_CASH",
                "1000",
                "initial",
            )
        )

        repo.insert_order_idempotent(
            order_payload(
                "order-entry",
                "client-entry",
                "BUY",
            )
        )

        repo.insert_order_idempotent(
            order_payload(
                "order-exit",
                "client-exit",
                "SELL",
            )
        )

        repo.insert_execution_idempotent(
            execution_payload(
                "execution-entry",
                "order-entry",
                "BUY",
                "100",
            )
        )

        repo.insert_execution_idempotent(
            execution_payload(
                "execution-exit",
                "order-exit",
                "SELL",
                "106.25",
            )
        )

        repo.save_position_idempotent(
            position_payload()
        )

        repo.append_portfolio_transaction_idempotent(
            transaction_payload(
                "txn-realized-1",
                "REALIZED_PNL",
                ledger_realized_pln,
                "trade-1",
            )
        )

        repo.append_trade_idempotent(
            trade_payload(
                realized_pln=trade_realized_pln,
            )
        )


def test_realized_pnl_reconciliation_uses_exact_decimal(repository):
    seed_closed_trade(
        repository,
        trade_realized_pln="25.0000",
        ledger_realized_pln="25",
    )

    result = repository.reconcile_realized_pnl()

    assert result["matches"] is True
    assert (
        result["trade_realized_pnl_pln"]
        == Decimal("25")
    )
    assert (
        result["ledger_realized_pnl_pln"]
        == Decimal("25")
    )
    assert result["trade_count"] == 1
    assert result["ledger_transaction_count"] == 1


def test_realized_pnl_amount_mismatch_fails_closed(repository):
    seed_closed_trade(
        repository,
        trade_realized_pln="24.99",
        ledger_realized_pln="25",
    )

    with pytest.raises(
        ReconciliationMismatchError,
        match="RECONCILIATION_MISMATCH",
    ):
        repository.reconcile_realized_pnl()


def test_reconcile_or_halt_persists_halt_on_realized_mismatch(repository):
    seed_closed_trade(
        repository,
        trade_realized_pln="24",
        ledger_realized_pln="25",
    )

    with pytest.raises(
        ReconciliationMismatchError,
        match="RECONCILIATION_MISMATCH",
    ):
        repository.reconcile_or_halt(
            updated_at_utc=NOW,
            event_id="event-halt-1",
            event_timestamp_utc=NOW,
        )

    state = repository.read_system_state()

    assert state["halted"] == 1
    assert (
        state["halt_reason"]
        == "RECONCILIATION_MISMATCH"
    )

    assert (
        repository.count_rows(
            "system_events"
        )
        == 1
    )


def test_halt_survives_database_reopen(tmp_path):
    path = tmp_path / "persistent-halt.db"

    repo = SQLiteLedgerRepository.open_writer(path)
    repo.initialize_schema(applied_at_utc=NOW)

    seed_closed_trade(
        repo,
        trade_realized_pln="24",
        ledger_realized_pln="25",
    )

    with pytest.raises(
        ReconciliationMismatchError
    ):
        repo.reconcile_or_halt(
            updated_at_utc=NOW,
            event_id="event-halt-persist",
            event_timestamp_utc=NOW,
        )

    repo.close()

    reopened = SQLiteLedgerRepository.open_writer(path)

    try:
        state = reopened.read_system_state()

        assert state["halted"] == 1
        assert (
            state["halt_reason"]
            == "RECONCILIATION_MISMATCH"
        )
    finally:
        reopened.close()


def test_successful_reconciliation_does_not_halt(repository):
    seed_closed_trade(
        repository,
        trade_realized_pln="25",
        ledger_realized_pln="25",
    )

    result = repository.reconcile_or_halt(
        updated_at_utc=NOW,
        event_id="unused-success-event",
        event_timestamp_utc=NOW,
    )

    assert result["cash"].matches is True
    assert result["realized"]["matches"] is True

    state = repository.read_system_state()

    assert state["halted"] == 0
    assert state["halt_reason"] is None
    assert repository.count_rows("system_events") == 0


def test_clear_halt_requires_explicit_reason_and_is_audited(repository):
    with repository.atomic_cycle():
        repository.initialize_system_state(
            cash_balance_pln="1000",
            updated_at_utc=NOW,
        )

        repository.set_halt(
            reason="RECONCILIATION_MISMATCH",
            updated_at_utc=NOW,
            event_id="halt-event",
            event_timestamp_utc=NOW,
        )

    with pytest.raises(
        ValueError,
        match="reason",
    ):
        with repository.atomic_cycle():
            repository.clear_halt_explicitly(
                reason="",
                updated_at_utc=NOW,
                event_id="clear-invalid",
                event_timestamp_utc=NOW,
            )

    with repository.atomic_cycle():
        repository.clear_halt_explicitly(
            reason="operator reconciliation verified",
            updated_at_utc=NOW,
            event_id="clear-event",
            event_timestamp_utc=NOW,
        )

    state = repository.read_system_state()

    assert state["halted"] == 0
    assert state["halt_reason"] is None
    assert repository.count_rows("system_events") == 2


def test_read_only_reader_observes_persistent_halt(tmp_path):
    path = tmp_path / "reader-halt.db"

    writer = SQLiteLedgerRepository.open_writer(path)
    writer.initialize_schema(applied_at_utc=NOW)

    with writer.atomic_cycle():
        writer.initialize_system_state(
            cash_balance_pln="1000",
            updated_at_utc=NOW,
        )

        writer.set_halt(
            reason="RECONCILIATION_MISMATCH",
            updated_at_utc=NOW,
            event_id="reader-halt-event",
            event_timestamp_utc=NOW,
        )

    writer.close()

    reader = SQLiteLedgerRepository.open_reader(path)

    try:
        state = reader.read_system_state()

        assert state["halted"] == 1
        assert (
            state["halt_reason"]
            == "RECONCILIATION_MISMATCH"
        )
    finally:
        reader.close()
