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
    SQLiteRuntimePersistenceHaltedError,
)
from src.persistence.sqlite_trade_cycle import (
    SQLiteTradeCycleCoordinator,
    SQLiteTradeCycleError,
)


T0 = "2026-09-18T23:00:00.000000Z"
T1 = "2026-09-18T23:01:00.000000Z"


def order_payload(
    *,
    order_id,
    client_order_id,
    side,
    intent,
    timestamp,
):
    return {
        "order_id": order_id,
        "client_order_id": client_order_id,
        "asset_id": "BTCUSDT",
        "strategy_id": "PHASE13_A14_TEST",
        "intent": intent,
        "side": side,
        "quantity_native": "1",
        "signal_reference": "PHASE13_A14",
        "source_timestamp_utc": timestamp,
        "created_at_utc": timestamp,
        "execution_profile": "REALISTIC_V2",
        "paper_mode": "realistic_paper",
        "status": "FILLED",
        "config_hash": "config-a14",
        "order_fingerprint": "fingerprint-" + client_order_id,
        "raw_json": {
            "phase": "13A14",
            "intent": intent,
        },
    }


def execution_payload(
    *,
    execution_id,
    order_id,
    side,
    price,
    timestamp,
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
        "provider_timestamp_utc": timestamp,
        "execution_timestamp_utc": timestamp,
        "data_quality": "REALTIME_BOOK",
        "execution_quality": "REAL_BOOK",
        "session_quality": "EXCHANGE_CALENDAR",
        "fx_path": "USDT->USD->PLN",
        "fx_rate": "4",
        "fx_provider": "TEST",
        "fx_timestamp_utc": timestamp,
        "fx_quality": "LIVE",
        "config_hash": "config-a14",
        "raw_json": {"phase": "13A14"},
    }


def open_position():
    return {
        "position_id": "position-a14",
        "asset_id": "BTCUSDT",
        "side": "LONG",
        "quantity_native": "1",
        "entry_execution_id": "execution-entry-a14",
        "exit_execution_id": None,
        "entry_price_native": "100",
        "exit_price_native": None,
        "stop_loss_native": "95",
        "take_profit_native": "110",
        "status": "OPEN",
        "opened_at_utc": T0,
        "closed_at_utc": None,
        "short_mechanism": None,
        "short_financing_model": None,
        "execution_profile": "REALISTIC_V2",
        "execution_quality_at_entry": "REAL_BOOK",
        "unrealized_pnl_native": "0",
        "unrealized_pnl_pln": "0",
        "raw_json": {
            "phase": "13A14",
            "state": "open",
        },
    }


def closed_position():
    result = dict(open_position())
    result.update(
        {
            "exit_execution_id": "execution-exit-a14",
            "exit_price_native": "106.25",
            "status": "CLOSED",
            "closed_at_utc": T1,
            "raw_json": {
                "phase": "13A14",
                "state": "closed",
            },
        }
    )
    return result


def trade_payload():
    return {
        "trade_id": "trade-a14",
        "asset_id": "BTCUSDT",
        "position_id": "position-a14",
        "entry_execution_id": "execution-entry-a14",
        "exit_execution_id": "execution-exit-a14",
        "quantity_native": "1",
        "realized_pnl_native": "6.25",
        "realized_pnl_pln": "25",
        "fees_pln": "0",
        "spread_cost_pln": "0",
        "slippage_pln": "0",
        "realized_fx_pair": "USDPLN",
        "realized_fx_path": "USDT->USD->PLN",
        "realized_fx_rate": "4",
        "realized_fx_provider": "TEST",
        "realized_fx_timestamp_utc": T1,
        "realized_fx_quality": "LIVE",
        "realized_transaction_id": "txn-realized-a14",
        "opened_at_utc": T0,
        "closed_at_utc": T1,
        "raw_json": {"phase": "13A14"},
    }


def transaction_payload():
    return {
        "transaction_id": "txn-realized-a14",
        "transaction_type": "REALIZED_PNL",
        "amount_pln": "25",
        "asset_id": "BTCUSDT",
        "reference_type": "TRADE",
        "reference_id": "trade-a14",
        "booked_at_utc": T1,
        "fx_pair": "USDPLN",
        "fx_path": "USDT->USD->PLN",
        "fx_rate": "4",
        "fx_provider": "TEST",
        "fx_timestamp_utc": T1,
        "fx_quality": "LIVE",
        "raw_json": {"phase": "13A14"},
    }


def create_activated_repo(path):
    bootstrap_fresh_database(
        path,
        initial_cash_pln="1000",
        bootstrap_id="phase13-a14-test",
        created_at_utc=T0,
    )

    repo = SQLiteLedgerRepository.open_writer(path)

    with repo.atomic_cycle():
        repo.clear_halt_explicitly(
            reason="A14 temporary integration activation",
            updated_at_utc=T0,
            event_id="a14-clear-bootstrap-halt",
            event_timestamp_utc=T0,
        )

    return repo


def persist_entry(repo):
    adapter = SQLiteRuntimePersistenceAdapter(repo)

    return adapter.persist_execution_cycle(
        processed_timestamp_utc=T0,
        updated_at_utc=T0,
        order=order_payload(
            order_id="order-entry-a14",
            client_order_id="client-entry-a14",
            side="BUY",
            intent="ENTRY",
            timestamp=T0,
        ),
        execution=execution_payload(
            execution_id="execution-entry-a14",
            order_id="order-entry-a14",
            side="BUY",
            price="100",
            timestamp=T0,
        ),
        position=open_position(),
    )


def set_test_halt(repo):
    with repo.atomic_cycle():
        repo.set_halt(
            reason="A14_TEST_HALT",
            updated_at_utc=T1,
            event_id="a14-test-halt",
            event_timestamp_utc=T1,
        )


def exit_args():
    return {
        "processed_timestamp_utc": T1,
        "updated_at_utc": T1,
        "reconciliation_event_id": "a14-reconcile",
        "order": order_payload(
            order_id="order-exit-a14",
            client_order_id="client-exit-a14",
            side="SELL",
            intent="EXIT",
            timestamp=T1,
        ),
        "execution": execution_payload(
            execution_id="execution-exit-a14",
            order_id="order-exit-a14",
            side="SELL",
            price="106.25",
            timestamp=T1,
        ),
        "closed_position": closed_position(),
        "trade": trade_payload(),
        "portfolio_transaction": transaction_payload(),
    }


def read_position(repo):
    row = repo.connection.execute(
        "SELECT * FROM positions WHERE position_id = ?",
        ("position-a14",),
    ).fetchone()
    return None if row is None else dict(row)


def realized_count(repo):
    row = repo.connection.execute(
        """
        SELECT COUNT(*) AS count_value
        FROM portfolio_transactions
        WHERE transaction_type = 'REALIZED_PNL'
        """
    ).fetchone()
    return int(row["count_value"])


def test_full_open_restart_halt_exit_financial_restart_replay(tmp_path):
    path = tmp_path / "a14-full-cycle.db"

    repo = create_activated_repo(path)
    entry = persist_entry(repo)

    assert entry.order_created is True
    assert entry.execution_created is True
    assert entry.position_created is True
    assert repo.read_last_processed_timestamp() == T0
    repo.close()

    repo = SQLiteLedgerRepository.open_writer(path)

    try:
        assert read_position(repo)["status"] == "OPEN"
        assert Decimal(
            repo.read_system_state()["cash_balance_pln"]
        ) == Decimal("1000")

        set_test_halt(repo)

        blocked_adapter = SQLiteRuntimePersistenceAdapter(repo)

        with pytest.raises(
            SQLiteRuntimePersistenceHaltedError,
            match="HALTED",
        ):
            blocked_adapter.persist_execution_cycle(
                processed_timestamp_utc=T1,
                updated_at_utc=T1,
                order=order_payload(
                    order_id="blocked-entry-a14",
                    client_order_id="blocked-entry-client-a14",
                    side="BUY",
                    intent="ENTRY",
                    timestamp=T1,
                ),
            )

        coordinator = SQLiteTradeCycleCoordinator(repo)

        first = coordinator.persist_exit_and_settle_cycle(
            **exit_args()
        )

        assert first.order_created is True
        assert first.execution_created is True
        assert first.position_closed is True
        assert first.trade_created is True
        assert first.transaction_created is True
        assert first.cash_balance_pln == Decimal("1025")

        state = repo.read_system_state()
        assert state["halted"] == 1
        assert state["halt_reason"] == "A14_TEST_HALT"

        assert read_position(repo)["status"] == "CLOSED"
        assert repo.count_rows("orders") == 2
        assert repo.count_rows("executions") == 2
        assert repo.count_rows("trades") == 1
        assert realized_count(repo) == 1
        assert repo.read_last_processed_timestamp() == T1
        assert repo.reconcile_cash().matches is True
        assert repo.reconcile_realized_pnl()["matches"] is True
    finally:
        repo.close()

    repo = SQLiteLedgerRepository.open_writer(path)

    try:
        coordinator = SQLiteTradeCycleCoordinator(repo)

        second = coordinator.persist_exit_and_settle_cycle(
            **exit_args()
        )

        assert second.order_created is False
        assert second.execution_created is False
        assert second.position_closed is False
        assert second.trade_created is False
        assert second.transaction_created is False
        assert second.cash_balance_pln == Decimal("1025")

        assert repo.count_rows("orders") == 2
        assert repo.count_rows("executions") == 2
        assert repo.count_rows("positions") == 1
        assert repo.count_rows("trades") == 1
        assert realized_count(repo) == 1
        assert read_position(repo)["status"] == "CLOSED"
        assert repo.read_last_processed_timestamp() == T1
        assert repo.reconcile_cash().matches is True
        assert repo.reconcile_realized_pnl()["matches"] is True

        state = repo.read_system_state()
        assert state["halted"] == 1
        assert state["halt_reason"] == "A14_TEST_HALT"
    finally:
        repo.close()


def test_exit_cycle_failure_rolls_back_order_execution_close_financial_and_timestamp(
    tmp_path,
    monkeypatch,
):
    path = tmp_path / "a14-rollback.db"

    repo = create_activated_repo(path)

    try:
        persist_entry(repo)
        set_test_halt(repo)

        coordinator = SQLiteTradeCycleCoordinator(repo)

        def fail_financial(**kwargs):
            raise RuntimeError("forced integrated financial failure")

        monkeypatch.setattr(
            coordinator.financial_unit_of_work,
            "settle_realized_inside_atomic_cycle",
            fail_financial,
        )

        with pytest.raises(
            RuntimeError,
            match="forced integrated financial failure",
        ):
            coordinator.persist_exit_and_settle_cycle(
                **exit_args()
            )

        assert repo.count_rows("orders") == 1
        assert repo.count_rows("executions") == 1
        assert repo.count_rows("trades") == 0
        assert realized_count(repo) == 0
        assert read_position(repo)["status"] == "OPEN"
        assert Decimal(
            repo.read_system_state()["cash_balance_pln"]
        ) == Decimal("1000")
        assert repo.read_last_processed_timestamp() == T0
    finally:
        repo.close()


def test_exit_coordinator_rejects_entry_intent_before_write(tmp_path):
    path = tmp_path / "a14-reject-entry.db"

    repo = create_activated_repo(path)

    try:
        persist_entry(repo)
        set_test_halt(repo)

        coordinator = SQLiteTradeCycleCoordinator(repo)
        args = exit_args()
        bad_order = dict(args["order"])
        bad_order["intent"] = "ENTRY"
        args["order"] = bad_order

        with pytest.raises(
            SQLiteTradeCycleError,
            match="EXIT",
        ):
            coordinator.persist_exit_and_settle_cycle(
                **args
            )

        assert repo.count_rows("orders") == 1
        assert repo.count_rows("executions") == 1
        assert read_position(repo)["status"] == "OPEN"
        assert Decimal(
            repo.read_system_state()["cash_balance_pln"]
        ) == Decimal("1000")
        assert repo.read_last_processed_timestamp() == T0
    finally:
        repo.close()


def test_exit_cycle_requires_closed_position_identity_match(tmp_path):
    path = tmp_path / "a14-position-mismatch.db"

    repo = create_activated_repo(path)

    try:
        persist_entry(repo)
        set_test_halt(repo)

        coordinator = SQLiteTradeCycleCoordinator(repo)
        args = exit_args()
        broken = dict(args["closed_position"])
        broken["position_id"] = "other-position"
        args["closed_position"] = broken

        with pytest.raises(Exception):
            coordinator.persist_exit_and_settle_cycle(
                **args
            )

        assert repo.count_rows("orders") == 1
        assert repo.count_rows("executions") == 1
        assert read_position(repo)["status"] == "OPEN"
        assert repo.read_last_processed_timestamp() == T0
    finally:
        repo.close()
