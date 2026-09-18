from decimal import Decimal

import pytest

from src.persistence.sqlite_repository import (
    IdempotencyConflictError,
    ReadOnlyRepositoryError,
    ReconciliationMismatchError,
    SQLiteLedgerRepository,
)


NOW = "2026-09-18T15:30:00.000000Z"


def order_payload(
    *,
    order_id="order-1",
    client_order_id="client-1",
    fingerprint="fingerprint-1",
    quantity="1.0000",
):
    return {
        "order_id": order_id,
        "client_order_id": client_order_id,
        "asset_id": "BTCUSDT",
        "strategy_id": "TEST",
        "intent": "ENTRY",
        "side": "BUY",
        "quantity_native": quantity,
        "signal_reference": "TEST_SIGNAL",
        "source_timestamp_utc": NOW,
        "created_at_utc": NOW,
        "execution_profile": "REALISTIC_V2",
        "paper_mode": "realistic_paper",
        "status": "PENDING",
        "config_hash": "config-1",
        "order_fingerprint": fingerprint,
        "raw_json": {
            "source": "phase13-test",
        },
    }


def execution_payload(
    *,
    execution_id="exec-1",
    execution_price="100.2500",
):
    return {
        "execution_id": execution_id,
        "order_id": "order-1",
        "asset_id": "BTCUSDT",
        "side": "BUY",
        "quantity_native": "1.0000",
        "reference_price_native": "100.00",
        "execution_price_native": execution_price,
        "bid_native": "99.90",
        "ask_native": "100.00",
        "spread_native": "0.10",
        "slippage_native": "0.25",
        "fee_native": "0.0401",
        "fee_pln": "0.1604",
        "provider_timestamp_utc": NOW,
        "execution_timestamp_utc": NOW,
        "data_quality": "REALTIME_BOOK",
        "execution_quality": "REAL_BOOK",
        "session_quality": "EXCHANGE_CALENDAR",
        "fx_path": "USDT->USD->PLN",
        "fx_rate": "4.0000",
        "fx_provider": "TEST",
        "fx_timestamp_utc": NOW,
        "fx_quality": "LIVE",
        "config_hash": "config-1",
        "raw_json": {
            "source": "phase13-test",
        },
    }


def transaction_payload(
    *,
    transaction_id="txn-1",
    amount="1000.0000",
    transaction_type="INITIAL_CASH",
):
    return {
        "transaction_id": transaction_id,
        "transaction_type": transaction_type,
        "amount_pln": amount,
        "asset_id": None,
        "reference_type": "TEST",
        "reference_id": "test-reference",
        "booked_at_utc": NOW,
        "fx_pair": None,
        "fx_path": None,
        "fx_rate": None,
        "fx_provider": None,
        "fx_timestamp_utc": None,
        "fx_quality": None,
        "raw_json": {
            "source": "phase13-test",
        },
    }


@pytest.fixture
def repository(tmp_path):
    path = tmp_path / "phase13_repository.db"

    repo = SQLiteLedgerRepository.open_writer(
        path,
        busy_timeout_ms=5000,
    )

    repo.initialize_schema(
        applied_at_utc=NOW,
    )

    try:
        yield repo
    finally:
        repo.close()


def test_writer_connection_enforces_required_pragmas(tmp_path):
    path = tmp_path / "pragma.db"

    repo = SQLiteLedgerRepository.open_writer(
        path,
        busy_timeout_ms=4321,
    )

    try:
        policy = repo.connection_policy()

        assert policy["journal_mode"] == "wal"
        assert policy["foreign_keys"] == 1
        assert policy["synchronous"] == 2
        assert policy["busy_timeout"] == 4321
        assert policy["query_only"] == 0
    finally:
        repo.close()


def test_schema_initialization_records_version_and_checksum(repository):
    version = repository.schema_version()

    assert version["version"] == 1
    assert (
        version["migration_name"]
        == "phase13_trading_schema_v1"
    )
    assert len(version["checksum_sha256"]) == 64


def test_schema_initialization_is_idempotent(repository):
    before = repository.schema_version()

    after = repository.initialize_schema(
        applied_at_utc=NOW,
    )

    assert after == before


def test_atomic_cycle_commits_all_changes(repository):
    with repository.atomic_cycle():
        row, created = repository.insert_order_idempotent(
            order_payload()
        )

        assert created is True
        assert row["client_order_id"] == "client-1"

    persisted = repository.get_order_by_client_order_id(
        "client-1"
    )

    assert persisted is not None
    assert persisted["order_id"] == "order-1"


def test_atomic_cycle_rolls_back_on_failure(repository):
    with pytest.raises(RuntimeError, match="force rollback"):
        with repository.atomic_cycle():
            repository.insert_order_idempotent(
                order_payload()
            )
            raise RuntimeError("force rollback")

    assert (
        repository.get_order_by_client_order_id(
            "client-1"
        )
        is None
    )


def test_exact_order_replay_is_idempotent(repository):
    with repository.atomic_cycle():
        first, first_created = (
            repository.insert_order_idempotent(
                order_payload()
            )
        )

    with repository.atomic_cycle():
        second, second_created = (
            repository.insert_order_idempotent(
                order_payload()
            )
        )

    assert first_created is True
    assert second_created is False
    assert first == second
    assert repository.count_rows("orders") == 1


def test_conflicting_client_order_id_fails_closed(repository):
    with repository.atomic_cycle():
        repository.insert_order_idempotent(
            order_payload()
        )

    conflicting = order_payload(
        order_id="order-2",
        client_order_id="client-1",
        fingerprint="different-fingerprint",
    )

    with pytest.raises(
        IdempotencyConflictError,
        match="client_order_id",
    ):
        with repository.atomic_cycle():
            repository.insert_order_idempotent(
                conflicting
            )

    assert repository.count_rows("orders") == 1


def test_execution_id_is_idempotent_and_conflict_safe(repository):
    with repository.atomic_cycle():
        repository.insert_order_idempotent(
            order_payload()
        )
        first, created = (
            repository.insert_execution_idempotent(
                execution_payload()
            )
        )

    assert created is True

    with repository.atomic_cycle():
        second, replay_created = (
            repository.insert_execution_idempotent(
                execution_payload()
            )
        )

    assert replay_created is False
    assert first == second

    with pytest.raises(
        IdempotencyConflictError,
        match="execution_id",
    ):
        with repository.atomic_cycle():
            repository.insert_execution_idempotent(
                execution_payload(
                    execution_price="101.00",
                )
            )

    assert repository.count_rows("executions") == 1


def test_transaction_id_is_idempotent_and_conflict_safe(repository):
    with repository.atomic_cycle():
        first, created = (
            repository.append_portfolio_transaction_idempotent(
                transaction_payload()
            )
        )

    assert created is True

    with repository.atomic_cycle():
        second, replay_created = (
            repository.append_portfolio_transaction_idempotent(
                transaction_payload()
            )
        )

    assert replay_created is False
    assert first == second

    with pytest.raises(
        IdempotencyConflictError,
        match="transaction_id",
    ):
        with repository.atomic_cycle():
            repository.append_portfolio_transaction_idempotent(
                transaction_payload(
                    amount="999.00",
                )
            )

    assert (
        repository.count_rows(
            "portfolio_transactions"
        )
        == 1
    )


def test_financial_values_are_canonical_decimal_text(repository):
    with repository.atomic_cycle():
        order, _ = repository.insert_order_idempotent(
            order_payload(
                quantity="1.2300",
            )
        )

        transaction, _ = (
            repository.append_portfolio_transaction_idempotent(
                transaction_payload(
                    amount="1000.5000",
                )
            )
        )

    assert order["quantity_native"] == "1.23"
    assert transaction["amount_pln"] == "1000.5"


def test_read_only_connection_can_read_but_not_write(tmp_path):
    path = tmp_path / "readonly.db"

    writer = SQLiteLedgerRepository.open_writer(
        path
    )

    writer.initialize_schema(
        applied_at_utc=NOW
    )

    with writer.atomic_cycle():
        writer.insert_order_idempotent(
            order_payload()
        )

    writer.close()

    reader = SQLiteLedgerRepository.open_reader(
        path
    )

    try:
        row = reader.get_order_by_client_order_id(
            "client-1"
        )

        assert row["order_id"] == "order-1"
        assert reader.connection_policy()["query_only"] == 1

        with pytest.raises(ReadOnlyRepositoryError):
            with reader.atomic_cycle():
                pass
    finally:
        reader.close()


def test_cash_reconciliation_uses_exact_decimal_arithmetic(repository):
    with repository.atomic_cycle():
        repository.initialize_system_state(
            cash_balance_pln="1000.1000",
            updated_at_utc=NOW,
        )

        repository.append_portfolio_transaction_idempotent(
            transaction_payload(
                transaction_id="txn-a",
                amount="500.05",
            )
        )

        repository.append_portfolio_transaction_idempotent(
            transaction_payload(
                transaction_id="txn-b",
                amount="500.0500",
            )
        )

    result = repository.reconcile_cash()

    assert result.ledger_cash_pln == Decimal("1000.10")
    assert result.state_cash_pln == Decimal("1000.10")
    assert result.matches is True


def test_cash_reconciliation_mismatch_fails_closed(repository):
    with repository.atomic_cycle():
        repository.initialize_system_state(
            cash_balance_pln="1000",
            updated_at_utc=NOW,
        )

        repository.append_portfolio_transaction_idempotent(
            transaction_payload(
                amount="999.99",
            )
        )

    with pytest.raises(
        ReconciliationMismatchError,
        match="RECONCILIATION_MISMATCH",
    ):
        repository.reconcile_cash()
