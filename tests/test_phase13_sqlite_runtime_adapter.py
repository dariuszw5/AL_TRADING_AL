from decimal import Decimal

import pytest

from src.persistence.sqlite_bootstrap import (
    bootstrap_fresh_database,
)
from src.persistence.sqlite_repository import (
    SQLiteLedgerRepository,
)
from src.persistence.sqlite_runtime_adapter import (
    SQLiteRuntimePersistenceAdapter,
    SQLiteRuntimePersistenceError,
    SQLiteRuntimePersistenceHaltedError,
)


NOW = "2026-09-18T20:00:00.000000Z"
NEXT = "2026-09-18T20:01:00.000000Z"


def order_payload(
    *,
    order_id="order-a11",
    client_order_id="client-a11",
    intent="ENTRY",
    side="BUY",
):
    return {
        "order_id": order_id,
        "client_order_id": client_order_id,
        "asset_id": "BTCUSDT",
        "strategy_id": "PHASE13_A11_TEST",
        "intent": intent,
        "side": side,
        "quantity_native": "1",
        "signal_reference": "PHASE13_A11",
        "source_timestamp_utc": NOW,
        "created_at_utc": NOW,
        "execution_profile": "REALISTIC_V2",
        "paper_mode": "realistic_paper",
        "status": "FILLED",
        "config_hash": "config-a11",
        "order_fingerprint": (
            "fingerprint-" + client_order_id
        ),
        "raw_json": {
            "phase": "13A11",
        },
    }


def execution_payload():
    return {
        "execution_id": "execution-a11",
        "order_id": "order-a11",
        "asset_id": "BTCUSDT",
        "side": "BUY",
        "quantity_native": "1",
        "reference_price_native": "100",
        "execution_price_native": "100.25",
        "bid_native": "99.90",
        "ask_native": "100",
        "spread_native": "0.10",
        "slippage_native": "0.25",
        "fee_native": "0.04",
        "fee_pln": "0.16",
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
        "config_hash": "config-a11",
        "raw_json": {
            "phase": "13A11",
        },
    }


def position_payload():
    return {
        "position_id": "position-a11",
        "asset_id": "BTCUSDT",
        "side": "LONG",
        "quantity_native": "1",
        "entry_execution_id": "execution-a11",
        "exit_execution_id": None,
        "entry_price_native": "100.25",
        "exit_price_native": None,
        "stop_loss_native": "95",
        "take_profit_native": "110",
        "status": "OPEN",
        "opened_at_utc": NOW,
        "closed_at_utc": None,
        "short_mechanism": None,
        "short_financing_model": None,
        "execution_profile": "REALISTIC_V2",
        "execution_quality_at_entry": "REAL_BOOK",
        "unrealized_pnl_native": "0",
        "unrealized_pnl_pln": "0",
        "raw_json": {
            "phase": "13A11",
        },
    }


def fresh_repository(tmp_path, *, clear_halt=False):
    path = tmp_path / "runtime-adapter.db"

    bootstrap_fresh_database(
        path,
        initial_cash_pln="1000",
        bootstrap_id="phase13-a11-test",
        created_at_utc=NOW,
    )

    repo = SQLiteLedgerRepository.open_writer(path)

    if clear_halt:
        with repo.atomic_cycle():
            repo.clear_halt_explicitly(
                reason="A11 temporary adapter test activation",
                updated_at_utc=NOW,
                event_id="a11-clear-halt",
                event_timestamp_utc=NOW,
            )

    return repo


def test_startup_snapshot_reads_halt_cash_and_timestamp(tmp_path):
    repo = fresh_repository(tmp_path)

    try:
        adapter = SQLiteRuntimePersistenceAdapter(repo)
        snapshot = adapter.startup_snapshot()

        assert snapshot.halted is True
        assert (
            snapshot.halt_reason
            == "FRESH_BOOTSTRAP_REQUIRES_EXPLICIT_ACTIVATION"
        )
        assert snapshot.cash_balance_pln == Decimal("1000")
        assert snapshot.last_processed_timestamp_utc is None
    finally:
        repo.close()


def test_halt_blocks_entry_before_any_write(tmp_path):
    repo = fresh_repository(tmp_path)

    try:
        adapter = SQLiteRuntimePersistenceAdapter(repo)

        with pytest.raises(
            SQLiteRuntimePersistenceHaltedError,
            match="HALTED",
        ):
            adapter.persist_execution_cycle(
                processed_timestamp_utc=NOW,
                updated_at_utc=NOW,
                order=order_payload(),
                execution=execution_payload(),
                position=position_payload(),
            )

        assert repo.count_rows("orders") == 0
        assert repo.count_rows("executions") == 0
        assert repo.count_rows("positions") == 0
        assert repo.read_last_processed_timestamp() is None
    finally:
        repo.close()


def test_halt_allows_exit_order_persistence(tmp_path):
    repo = fresh_repository(tmp_path)

    try:
        adapter = SQLiteRuntimePersistenceAdapter(repo)

        result = adapter.persist_execution_cycle(
            processed_timestamp_utc=NOW,
            updated_at_utc=NOW,
            order=order_payload(
                order_id="order-exit-a11",
                client_order_id="client-exit-a11",
                intent="EXIT",
                side="SELL",
            ),
        )

        assert result.order_created is True
        assert repo.count_rows("orders") == 1
        assert repo.read_last_processed_timestamp() == NOW
    finally:
        repo.close()


def test_entry_cycle_commits_order_execution_position_and_timestamp(
    tmp_path,
):
    repo = fresh_repository(
        tmp_path,
        clear_halt=True,
    )

    try:
        adapter = SQLiteRuntimePersistenceAdapter(repo)

        result = adapter.persist_execution_cycle(
            processed_timestamp_utc=NOW,
            updated_at_utc=NOW,
            order=order_payload(),
            execution=execution_payload(),
            position=position_payload(),
        )

        assert result.order_created is True
        assert result.execution_created is True
        assert result.position_created is True

        assert repo.count_rows("orders") == 1
        assert repo.count_rows("executions") == 1
        assert repo.count_rows("positions") == 1
        assert repo.read_last_processed_timestamp() == NOW
    finally:
        repo.close()


def test_exact_cycle_replay_is_idempotent(tmp_path):
    repo = fresh_repository(
        tmp_path,
        clear_halt=True,
    )

    try:
        adapter = SQLiteRuntimePersistenceAdapter(repo)

        first = adapter.persist_execution_cycle(
            processed_timestamp_utc=NOW,
            updated_at_utc=NOW,
            order=order_payload(),
            execution=execution_payload(),
            position=position_payload(),
        )

        second = adapter.persist_execution_cycle(
            processed_timestamp_utc=NOW,
            updated_at_utc=NOW,
            order=order_payload(),
            execution=execution_payload(),
            position=position_payload(),
        )

        assert first.order_created is True
        assert first.execution_created is True
        assert first.position_created is True

        assert second.order_created is False
        assert second.execution_created is False
        assert second.position_created is False

        assert repo.count_rows("orders") == 1
        assert repo.count_rows("executions") == 1
        assert repo.count_rows("positions") == 1
        assert repo.read_last_processed_timestamp() == NOW
    finally:
        repo.close()


def test_failure_rolls_back_order_and_timestamp(tmp_path, monkeypatch):
    repo = fresh_repository(
        tmp_path,
        clear_halt=True,
    )

    try:
        adapter = SQLiteRuntimePersistenceAdapter(repo)

        def fail_execution(payload):
            raise RuntimeError("forced execution persistence failure")

        monkeypatch.setattr(
            repo,
            "insert_execution_idempotent",
            fail_execution,
        )

        with pytest.raises(
            RuntimeError,
            match="forced execution persistence failure",
        ):
            adapter.persist_execution_cycle(
                processed_timestamp_utc=NOW,
                updated_at_utc=NOW,
                order=order_payload(),
                execution=execution_payload(),
                position=position_payload(),
            )

        assert repo.count_rows("orders") == 0
        assert repo.count_rows("executions") == 0
        assert repo.count_rows("positions") == 0
        assert repo.read_last_processed_timestamp() is None
    finally:
        repo.close()


def test_processed_timestamp_requires_nonempty_value(tmp_path):
    repo = fresh_repository(
        tmp_path,
        clear_halt=True,
    )

    try:
        adapter = SQLiteRuntimePersistenceAdapter(repo)

        with pytest.raises(
            SQLiteRuntimePersistenceError,
            match="processed_timestamp",
        ):
            adapter.persist_execution_cycle(
                processed_timestamp_utc="",
                updated_at_utc=NOW,
            )
    finally:
        repo.close()


def test_adapter_does_not_expose_financial_cycle_arguments(tmp_path):
    repo = fresh_repository(
        tmp_path,
        clear_halt=True,
    )

    try:
        adapter = SQLiteRuntimePersistenceAdapter(repo)

        with pytest.raises(TypeError):
            adapter.persist_execution_cycle(
                processed_timestamp_utc=NEXT,
                updated_at_utc=NEXT,
                portfolio_transaction={
                    "transaction_id": "not-allowed-a11",
                },
            )

        assert repo.count_rows("portfolio_transactions") == 1
        assert repo.count_rows("trades") == 0
    finally:
        repo.close()
