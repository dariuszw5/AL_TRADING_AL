import pytest

from src.persistence.sqlite_repository import (
    SQLiteLedgerRepository,
    SQLiteLedgerRepositoryError,
)


NOW = "2026-09-18T17:00:00.000000Z"
NEXT = "2026-09-18T17:01:00.000000Z"


def order_payload():
    return {
        "order_id": "order-a5",
        "client_order_id": "client-a5",
        "asset_id": "BTCUSDT",
        "strategy_id": "TEST",
        "intent": "ENTRY",
        "side": "BUY",
        "quantity_native": "1",
        "signal_reference": "PHASE13_A5",
        "source_timestamp_utc": NOW,
        "created_at_utc": NOW,
        "execution_profile": "REALISTIC_V2",
        "paper_mode": "realistic_paper",
        "status": "FILLED",
        "config_hash": "config-a5",
        "order_fingerprint": "fingerprint-a5",
        "raw_json": {
            "phase": "13A5",
        },
    }


def transaction_payload():
    return {
        "transaction_id": "txn-a5",
        "transaction_type": "TEST_FINANCIAL_EFFECT",
        "amount_pln": "5.25",
        "asset_id": "BTCUSDT",
        "reference_type": "TEST",
        "reference_id": "cycle-a5",
        "booked_at_utc": NOW,
        "fx_pair": None,
        "fx_path": None,
        "fx_rate": None,
        "fx_provider": None,
        "fx_timestamp_utc": None,
        "fx_quality": None,
        "raw_json": {
            "phase": "13A5",
        },
    }


@pytest.fixture
def repository(tmp_path):
    path = tmp_path / "phase13_a5.db"

    repo = SQLiteLedgerRepository.open_writer(path)
    repo.initialize_schema(applied_at_utc=NOW)

    with repo.atomic_cycle():
        repo.initialize_system_state(
            cash_balance_pln="1000",
            updated_at_utc=NOW,
        )

    try:
        yield repo
    finally:
        repo.close()


def test_processed_timestamp_requires_atomic_cycle(repository):
    with pytest.raises(
        SQLiteLedgerRepositoryError,
        match="atomic_cycle",
    ):
        repository.set_last_processed_timestamp(
            processed_timestamp_utc=NOW,
            updated_at_utc=NOW,
        )


def test_empty_processed_timestamp_is_rejected(repository):
    with pytest.raises(
        ValueError,
        match="processed_timestamp",
    ):
        with repository.atomic_cycle():
            repository.set_last_processed_timestamp(
                processed_timestamp_utc="",
                updated_at_utc=NOW,
            )


def test_financial_effects_and_processed_timestamp_commit_together(repository):
    with repository.atomic_cycle():
        repository.insert_order_idempotent(
            order_payload()
        )

        repository.append_portfolio_transaction_idempotent(
            transaction_payload()
        )

        repository.set_last_processed_timestamp(
            processed_timestamp_utc=NOW,
            updated_at_utc=NOW,
        )

    assert repository.count_rows("orders") == 1

    assert (
        repository.count_rows(
            "portfolio_transactions"
        )
        == 1
    )

    assert (
        repository.read_last_processed_timestamp()
        == NOW
    )


def test_failure_rolls_back_timestamp_and_all_financial_effects(repository):
    with pytest.raises(
        RuntimeError,
        match="forced cycle failure",
    ):
        with repository.atomic_cycle():
            repository.insert_order_idempotent(
                order_payload()
            )

            repository.append_portfolio_transaction_idempotent(
                transaction_payload()
            )

            repository.set_last_processed_timestamp(
                processed_timestamp_utc=NOW,
                updated_at_utc=NOW,
            )

            raise RuntimeError(
                "forced cycle failure"
            )

    assert repository.count_rows("orders") == 0

    assert (
        repository.count_rows(
            "portfolio_transactions"
        )
        == 0
    )

    assert (
        repository.read_last_processed_timestamp()
        is None
    )


def test_failure_after_timestamp_update_restores_previous_timestamp(repository):
    with repository.atomic_cycle():
        repository.set_last_processed_timestamp(
            processed_timestamp_utc=NOW,
            updated_at_utc=NOW,
        )

    assert (
        repository.read_last_processed_timestamp()
        == NOW
    )

    with pytest.raises(
        RuntimeError,
        match="after timestamp",
    ):
        with repository.atomic_cycle():
            repository.set_last_processed_timestamp(
                processed_timestamp_utc=NEXT,
                updated_at_utc=NEXT,
            )

            repository.insert_order_idempotent(
                order_payload()
            )

            raise RuntimeError(
                "after timestamp"
            )

    assert (
        repository.read_last_processed_timestamp()
        == NOW
    )

    assert repository.count_rows("orders") == 0


def test_exact_cycle_replay_does_not_duplicate_financial_rows(repository):
    with repository.atomic_cycle():
        first_order, first_order_created = (
            repository.insert_order_idempotent(
                order_payload()
            )
        )

        first_txn, first_txn_created = (
            repository.append_portfolio_transaction_idempotent(
                transaction_payload()
            )
        )

        repository.set_last_processed_timestamp(
            processed_timestamp_utc=NOW,
            updated_at_utc=NOW,
        )

    with repository.atomic_cycle():
        second_order, second_order_created = (
            repository.insert_order_idempotent(
                order_payload()
            )
        )

        second_txn, second_txn_created = (
            repository.append_portfolio_transaction_idempotent(
                transaction_payload()
            )
        )

        repository.set_last_processed_timestamp(
            processed_timestamp_utc=NOW,
            updated_at_utc=NOW,
        )

    assert first_order_created is True
    assert second_order_created is False

    assert first_txn_created is True
    assert second_txn_created is False

    assert first_order == second_order
    assert first_txn == second_txn

    assert repository.count_rows("orders") == 1

    assert (
        repository.count_rows(
            "portfolio_transactions"
        )
        == 1
    )

    assert (
        repository.read_last_processed_timestamp()
        == NOW
    )


def test_processed_timestamp_survives_database_reopen(tmp_path):
    path = tmp_path / "phase13-a5-persistent.db"

    writer = SQLiteLedgerRepository.open_writer(path)
    writer.initialize_schema(applied_at_utc=NOW)

    with writer.atomic_cycle():
        writer.initialize_system_state(
            cash_balance_pln="1000",
            updated_at_utc=NOW,
        )

        writer.set_last_processed_timestamp(
            processed_timestamp_utc=NOW,
            updated_at_utc=NOW,
        )

    writer.close()

    reopened = SQLiteLedgerRepository.open_writer(path)

    try:
        assert (
            reopened.read_last_processed_timestamp()
            == NOW
        )
    finally:
        reopened.close()


def test_read_only_reader_can_observe_processed_timestamp(tmp_path):
    path = tmp_path / "phase13-a5-reader.db"

    writer = SQLiteLedgerRepository.open_writer(path)
    writer.initialize_schema(applied_at_utc=NOW)

    with writer.atomic_cycle():
        writer.initialize_system_state(
            cash_balance_pln="1000",
            updated_at_utc=NOW,
        )

        writer.set_last_processed_timestamp(
            processed_timestamp_utc=NOW,
            updated_at_utc=NOW,
        )

    writer.close()

    reader = SQLiteLedgerRepository.open_reader(path)

    try:
        assert (
            reader.read_last_processed_timestamp()
            == NOW
        )
    finally:
        reader.close()
