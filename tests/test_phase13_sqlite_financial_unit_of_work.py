from decimal import Decimal

import pytest

from src.persistence.sqlite_bootstrap import (
    bootstrap_fresh_database,
)
from src.persistence.sqlite_financial_unit_of_work import (
    SQLiteFinancialUnitOfWork,
    SQLiteFinancialUnitOfWorkError,
)
from src.persistence.sqlite_repository import (
    ReconciliationMismatchError,
    SQLiteLedgerRepository,
)


NOW = "2026-09-18T21:00:00.000000Z"
NEXT = "2026-09-18T21:01:00.000000Z"


def order_payload(
    order_id,
    client_order_id,
    side,
):
    return {
        "order_id": order_id,
        "client_order_id": client_order_id,
        "asset_id": "BTCUSDT",
        "strategy_id": "PHASE13_A12_TEST",
        "intent": (
            "ENTRY"
            if side == "BUY"
            else "EXIT"
        ),
        "side": side,
        "quantity_native": "1",
        "signal_reference": "PHASE13_A12",
        "source_timestamp_utc": NOW,
        "created_at_utc": NOW,
        "execution_profile": "REALISTIC_V2",
        "paper_mode": "realistic_paper",
        "status": "FILLED",
        "config_hash": "config-a12",
        "order_fingerprint": (
            "fingerprint-" + client_order_id
        ),
        "raw_json": {
            "phase": "13A12",
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
        "config_hash": "config-a12",
        "raw_json": {
            "phase": "13A12",
        },
    }


def position_payload():
    return {
        "position_id": "position-a12",
        "asset_id": "BTCUSDT",
        "side": "LONG",
        "quantity_native": "1",
        "entry_execution_id": "execution-entry-a12",
        "exit_execution_id": "execution-exit-a12",
        "entry_price_native": "100",
        "exit_price_native": "106.25",
        "stop_loss_native": "95",
        "take_profit_native": "110",
        "status": "CLOSED",
        "opened_at_utc": NOW,
        "closed_at_utc": NEXT,
        "short_mechanism": None,
        "short_financing_model": None,
        "execution_profile": "REALISTIC_V2",
        "execution_quality_at_entry": "REAL_BOOK",
        "unrealized_pnl_native": "0",
        "unrealized_pnl_pln": "0",
        "raw_json": {
            "phase": "13A12",
        },
    }


def trade_payload(
    *,
    realized_pln="25",
):
    return {
        "trade_id": "trade-a12",
        "asset_id": "BTCUSDT",
        "position_id": "position-a12",
        "entry_execution_id": "execution-entry-a12",
        "exit_execution_id": "execution-exit-a12",
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
        "realized_fx_timestamp_utc": NEXT,
        "realized_fx_quality": "LIVE",
        "realized_transaction_id": "txn-realized-a12",
        "opened_at_utc": NOW,
        "closed_at_utc": NEXT,
        "raw_json": {
            "phase": "13A12",
        },
    }


def transaction_payload(
    *,
    amount="25",
):
    return {
        "transaction_id": "txn-realized-a12",
        "transaction_type": "REALIZED_PNL",
        "amount_pln": amount,
        "asset_id": "BTCUSDT",
        "reference_type": "TRADE",
        "reference_id": "trade-a12",
        "booked_at_utc": NEXT,
        "fx_pair": "USDPLN",
        "fx_path": "USDT->USD->PLN",
        "fx_rate": "4",
        "fx_provider": "TEST",
        "fx_timestamp_utc": NEXT,
        "fx_quality": "LIVE",
        "raw_json": {
            "phase": "13A12",
        },
    }


def build_repo(tmp_path):
    path = tmp_path / "financial-uow.db"

    bootstrap_fresh_database(
        path,
        initial_cash_pln="1000",
        bootstrap_id="phase13-a12-test",
        created_at_utc=NOW,
    )

    repo = SQLiteLedgerRepository.open_writer(path)

    with repo.atomic_cycle():
        repo.insert_order_idempotent(
            order_payload(
                "order-entry-a12",
                "client-entry-a12",
                "BUY",
            )
        )

        repo.insert_order_idempotent(
            order_payload(
                "order-exit-a12",
                "client-exit-a12",
                "SELL",
            )
        )

        repo.insert_execution_idempotent(
            execution_payload(
                "execution-entry-a12",
                "order-entry-a12",
                "BUY",
                "100",
            )
        )

        repo.insert_execution_idempotent(
            execution_payload(
                "execution-exit-a12",
                "order-exit-a12",
                "SELL",
                "106.25",
            )
        )

        repo.save_position_idempotent(
            position_payload()
        )

    return repo


def realized_transaction_count(repo):
    row = repo.connection.execute(
        """
        SELECT COUNT(*) AS count_value
        FROM portfolio_transactions
        WHERE transaction_type = 'REALIZED_PNL'
        """
    ).fetchone()

    return int(row["count_value"])


def test_realized_profit_updates_cash_trade_ledger_and_timestamp(tmp_path):
    repo = build_repo(tmp_path)

    try:
        uow = SQLiteFinancialUnitOfWork(repo)

        result = uow.settle_realized_cycle(
            processed_timestamp_utc=NEXT,
            updated_at_utc=NEXT,
            reconciliation_event_id="reconcile-a12-profit",
            trade=trade_payload(
                realized_pln="25",
            ),
            portfolio_transaction=transaction_payload(
                amount="25",
            ),
        )

        assert result.trade_created is True
        assert result.transaction_created is True
        assert result.cash_balance_pln == Decimal("1025")
        assert result.cash_reconciliation_matches is True
        assert result.realized_reconciliation_matches is True

        state = repo.read_system_state()

        assert Decimal(
            state["cash_balance_pln"]
        ) == Decimal("1025")

        assert repo.count_rows("trades") == 1
        assert realized_transaction_count(repo) == 1
        assert repo.read_last_processed_timestamp() == NEXT
    finally:
        repo.close()


def test_realized_loss_updates_cash_exactly(tmp_path):
    repo = build_repo(tmp_path)

    try:
        uow = SQLiteFinancialUnitOfWork(repo)

        result = uow.settle_realized_cycle(
            processed_timestamp_utc=NEXT,
            updated_at_utc=NEXT,
            reconciliation_event_id="reconcile-a12-loss",
            trade=trade_payload(
                realized_pln="-40",
            ),
            portfolio_transaction=transaction_payload(
                amount="-40",
            ),
        )

        assert result.cash_balance_pln == Decimal("960")
        assert repo.reconcile_cash().matches is True
        assert repo.reconcile_realized_pnl()["matches"] is True
    finally:
        repo.close()


def test_exact_replay_does_not_double_book_cash(tmp_path):
    repo = build_repo(tmp_path)

    try:
        uow = SQLiteFinancialUnitOfWork(repo)

        first = uow.settle_realized_cycle(
            processed_timestamp_utc=NEXT,
            updated_at_utc=NEXT,
            reconciliation_event_id="reconcile-a12-replay-1",
            trade=trade_payload(),
            portfolio_transaction=transaction_payload(),
        )

        second = uow.settle_realized_cycle(
            processed_timestamp_utc=NEXT,
            updated_at_utc=NEXT,
            reconciliation_event_id="reconcile-a12-replay-2",
            trade=trade_payload(),
            portfolio_transaction=transaction_payload(),
        )

        assert first.trade_created is True
        assert first.transaction_created is True
        assert second.trade_created is False
        assert second.transaction_created is False

        assert Decimal(
            repo.read_system_state()["cash_balance_pln"]
        ) == Decimal("1025")

        assert repo.count_rows("trades") == 1
        assert realized_transaction_count(repo) == 1
    finally:
        repo.close()


def test_failure_after_cash_update_rolls_back_everything(
    tmp_path,
    monkeypatch,
):
    repo = build_repo(tmp_path)

    try:
        uow = SQLiteFinancialUnitOfWork(repo)

        def fail_timestamp(**kwargs):
            raise RuntimeError("forced timestamp failure")

        monkeypatch.setattr(
            repo,
            "set_last_processed_timestamp",
            fail_timestamp,
        )

        with pytest.raises(
            RuntimeError,
            match="forced timestamp failure",
        ):
            uow.settle_realized_cycle(
                processed_timestamp_utc=NEXT,
                updated_at_utc=NEXT,
                reconciliation_event_id="reconcile-a12-rollback",
                trade=trade_payload(),
                portfolio_transaction=transaction_payload(),
            )

        assert Decimal(
            repo.read_system_state()["cash_balance_pln"]
        ) == Decimal("1000")

        assert repo.count_rows("trades") == 0
        assert realized_transaction_count(repo) == 0
        assert repo.read_last_processed_timestamp() is None
        assert repo.reconcile_cash().matches is True
        assert repo.reconcile_realized_pnl()["matches"] is True
    finally:
        repo.close()


def test_trade_and_ledger_amount_must_match_before_write(tmp_path):
    repo = build_repo(tmp_path)

    try:
        uow = SQLiteFinancialUnitOfWork(repo)

        with pytest.raises(
            SQLiteFinancialUnitOfWorkError,
            match="realized PnL",
        ):
            uow.settle_realized_cycle(
                processed_timestamp_utc=NEXT,
                updated_at_utc=NEXT,
                reconciliation_event_id="reconcile-a12-mismatch",
                trade=trade_payload(
                    realized_pln="25",
                ),
                portfolio_transaction=transaction_payload(
                    amount="24.99",
                ),
            )

        assert repo.count_rows("trades") == 0
        assert realized_transaction_count(repo) == 0
        assert Decimal(
            repo.read_system_state()["cash_balance_pln"]
        ) == Decimal("1000")
    finally:
        repo.close()


def test_realized_transaction_identity_must_link_trade(tmp_path):
    repo = build_repo(tmp_path)

    try:
        uow = SQLiteFinancialUnitOfWork(repo)
        transaction = transaction_payload()
        transaction["reference_id"] = "other-trade"

        with pytest.raises(
            SQLiteFinancialUnitOfWorkError,
            match="reference_id",
        ):
            uow.settle_realized_cycle(
                processed_timestamp_utc=NEXT,
                updated_at_utc=NEXT,
                reconciliation_event_id="reconcile-a12-link",
                trade=trade_payload(),
                portfolio_transaction=transaction,
            )
    finally:
        repo.close()


def test_preexisting_cash_mismatch_persists_reconciliation_halt(
    tmp_path,
):
    repo = build_repo(tmp_path)

    try:
        with repo.atomic_cycle():
            repo.clear_halt_explicitly(
                reason="temporary A12 mismatch test activation",
                updated_at_utc=NOW,
                event_id="a12-clear-for-mismatch",
                event_timestamp_utc=NOW,
            )

        repo.connection.execute(
            """
            UPDATE system_state
            SET cash_balance_pln = '999'
            """
        )
        repo.connection.commit()

        uow = SQLiteFinancialUnitOfWork(repo)

        with pytest.raises(
            ReconciliationMismatchError,
            match="RECONCILIATION_MISMATCH",
        ):
            uow.settle_realized_cycle(
                processed_timestamp_utc=NEXT,
                updated_at_utc=NEXT,
                reconciliation_event_id="a12-preflight-halt",
                trade=trade_payload(),
                portfolio_transaction=transaction_payload(),
            )

        state = repo.read_system_state()

        assert state["halted"] == 1
        assert (
            state["halt_reason"]
            == "RECONCILIATION_MISMATCH"
        )

        assert repo.count_rows("trades") == 0
        assert realized_transaction_count(repo) == 0
        assert repo.read_last_processed_timestamp() is None
    finally:
        repo.close()


def test_financial_exit_settlement_is_allowed_while_halted(tmp_path):
    repo = build_repo(tmp_path)

    try:
        state_before = repo.read_system_state()
        assert state_before["halted"] == 1

        uow = SQLiteFinancialUnitOfWork(repo)

        result = uow.settle_realized_cycle(
            processed_timestamp_utc=NEXT,
            updated_at_utc=NEXT,
            reconciliation_event_id="reconcile-a12-halted-exit",
            trade=trade_payload(),
            portfolio_transaction=transaction_payload(),
        )

        state_after = repo.read_system_state()

        assert result.cash_balance_pln == Decimal("1025")
        assert state_after["halted"] == 1
        assert (
            state_after["halt_reason"]
            == "FRESH_BOOTSTRAP_REQUIRES_EXPLICIT_ACTIVATION"
        )
    finally:
        repo.close()


def test_only_realized_pnl_transaction_is_accepted(tmp_path):
    repo = build_repo(tmp_path)

    try:
        uow = SQLiteFinancialUnitOfWork(repo)
        transaction = transaction_payload()
        transaction["transaction_type"] = "TEST_FINANCIAL_EFFECT"

        with pytest.raises(
            SQLiteFinancialUnitOfWorkError,
            match="REALIZED_PNL",
        ):
            uow.settle_realized_cycle(
                processed_timestamp_utc=NEXT,
                updated_at_utc=NEXT,
                reconciliation_event_id="reconcile-a12-type",
                trade=trade_payload(),
                portfolio_transaction=transaction,
            )
    finally:
        repo.close()
