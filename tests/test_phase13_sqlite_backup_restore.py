import sqlite3

import pytest

from src.persistence.sqlite_repository import (
    SQLiteLedgerRepository,
    SQLiteLedgerRepositoryError,
)


NOW = "2026-09-18T18:00:00.000000Z"


def order_payload(
    *,
    order_id="order-a6",
    client_order_id="client-a6",
    fingerprint="fingerprint-a6",
):
    return {
        "order_id": order_id,
        "client_order_id": client_order_id,
        "asset_id": "BTCUSDT",
        "strategy_id": "TEST",
        "intent": "ENTRY",
        "side": "BUY",
        "quantity_native": "1",
        "signal_reference": "PHASE13_A6",
        "source_timestamp_utc": NOW,
        "created_at_utc": NOW,
        "execution_profile": "REALISTIC_V2",
        "paper_mode": "realistic_paper",
        "status": "FILLED",
        "config_hash": "config-a6",
        "order_fingerprint": fingerprint,
        "raw_json": {
            "phase": "13A6",
        },
    }


def transaction_payload():
    return {
        "transaction_id": "txn-initial-a6",
        "transaction_type": "INITIAL_CASH",
        "amount_pln": "1000",
        "asset_id": None,
        "reference_type": "STARTUP",
        "reference_id": "phase13-a6",
        "booked_at_utc": NOW,
        "fx_pair": None,
        "fx_path": None,
        "fx_rate": None,
        "fx_provider": None,
        "fx_timestamp_utc": None,
        "fx_quality": None,
        "raw_json": {
            "phase": "13A6",
        },
    }


def create_seeded_repository(path):
    repo = SQLiteLedgerRepository.open_writer(path)
    repo.initialize_schema(applied_at_utc=NOW)

    with repo.atomic_cycle():
        repo.initialize_system_state(
            cash_balance_pln="1000",
            updated_at_utc=NOW,
        )

        repo.append_portfolio_transaction_idempotent(
            transaction_payload()
        )

        repo.insert_order_idempotent(
            order_payload()
        )

        repo.set_last_processed_timestamp(
            processed_timestamp_utc=NOW,
            updated_at_utc=NOW,
        )

        repo.set_halt(
            reason="TEST_HALT_A6",
            updated_at_utc=NOW,
            event_id="halt-a6",
            event_timestamp_utc=NOW,
        )

    return repo


def test_backup_creates_verified_sqlite_snapshot(tmp_path):
    source = tmp_path / "source.db"
    backup = tmp_path / "backup.db"

    repo = create_seeded_repository(source)

    try:
        result = repo.backup_to(backup)
    finally:
        repo.close()

    assert backup.exists()
    assert result["integrity_ok"] is True
    assert result["foreign_keys_ok"] is True
    assert result["schema_version"] == 1


def test_backup_contains_committed_financial_state(tmp_path):
    source = tmp_path / "source.db"
    backup = tmp_path / "backup.db"

    repo = create_seeded_repository(source)

    try:
        repo.backup_to(backup)
    finally:
        repo.close()

    reader = SQLiteLedgerRepository.open_reader(backup)

    try:
        assert reader.count_rows("orders") == 1

        assert (
            reader.count_rows(
                "portfolio_transactions"
            )
            == 1
        )

        assert (
            reader.read_last_processed_timestamp()
            == NOW
        )

        state = reader.read_system_state()

        assert state["halted"] == 1
        assert state["halt_reason"] == "TEST_HALT_A6"
    finally:
        reader.close()


def test_backup_is_point_in_time_snapshot(tmp_path):
    source = tmp_path / "source.db"
    backup = tmp_path / "backup.db"

    repo = create_seeded_repository(source)

    repo.backup_to(backup)

    with repo.atomic_cycle():
        repo.insert_order_idempotent(
            order_payload(
                order_id="order-after-backup",
                client_order_id="client-after-backup",
                fingerprint="fingerprint-after-backup",
            )
        )

    assert repo.count_rows("orders") == 2

    repo.close()

    backup_reader = SQLiteLedgerRepository.open_reader(
        backup
    )

    try:
        assert backup_reader.count_rows("orders") == 1
    finally:
        backup_reader.close()


def test_backup_refuses_existing_destination(tmp_path):
    source = tmp_path / "source.db"
    backup = tmp_path / "backup.db"

    repo = create_seeded_repository(source)

    backup.write_bytes(b"already exists")

    try:
        with pytest.raises(
            FileExistsError,
            match="already exists",
        ):
            repo.backup_to(backup)
    finally:
        repo.close()


def test_backup_refuses_active_atomic_cycle(tmp_path):
    source = tmp_path / "source.db"
    backup = tmp_path / "backup.db"

    repo = create_seeded_repository(source)

    try:
        with pytest.raises(
            SQLiteLedgerRepositoryError,
            match="active atomic_cycle",
        ):
            with repo.atomic_cycle():
                repo.backup_to(backup)
    finally:
        repo.close()

    assert backup.exists() is False


def test_restore_recreates_verified_database(tmp_path):
    source = tmp_path / "source.db"
    backup = tmp_path / "backup.db"
    restored = tmp_path / "restored.db"

    repo = create_seeded_repository(source)

    try:
        repo.backup_to(backup)
    finally:
        repo.close()

    restored_repo = (
        SQLiteLedgerRepository.restore_from_backup(
            backup,
            restored,
        )
    )

    try:
        assert restored_repo.count_rows("orders") == 1

        assert (
            restored_repo.count_rows(
                "portfolio_transactions"
            )
            == 1
        )

        assert (
            restored_repo.read_last_processed_timestamp()
            == NOW
        )

        state = restored_repo.read_system_state()

        assert state["halted"] == 1
        assert state["halt_reason"] == "TEST_HALT_A6"

        reconciliation = (
            restored_repo.reconcile_cash()
        )

        assert reconciliation.matches is True

    finally:
        restored_repo.close()


def test_restore_refuses_existing_destination(tmp_path):
    source = tmp_path / "source.db"
    backup = tmp_path / "backup.db"
    restored = tmp_path / "restored.db"

    repo = create_seeded_repository(source)

    try:
        repo.backup_to(backup)
    finally:
        repo.close()

    restored.write_bytes(b"existing")

    with pytest.raises(
        FileExistsError,
        match="already exists",
    ):
        SQLiteLedgerRepository.restore_from_backup(
            backup,
            restored,
        )


def test_corrupted_backup_fails_verification(tmp_path):
    corrupt = tmp_path / "corrupt.db"

    corrupt.write_bytes(
        b"this is not a sqlite database"
    )

    with pytest.raises(
        SQLiteLedgerRepositoryError,
        match="verification",
    ):
        SQLiteLedgerRepository.verify_database_file(
            corrupt
        )


def test_foreign_key_corruption_fails_verification(tmp_path):
    source = tmp_path / "source.db"
    backup = tmp_path / "backup.db"

    repo = create_seeded_repository(source)

    try:
        repo.backup_to(backup)
    finally:
        repo.close()

    raw = sqlite3.connect(str(backup))

    try:
        raw.execute("PRAGMA foreign_keys=OFF")

        raw.execute(
            """
            INSERT INTO executions (
                execution_id,
                order_id,
                asset_id,
                side,
                quantity_native,
                execution_price_native,
                execution_timestamp_utc
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "broken-execution",
                "missing-order",
                "BTCUSDT",
                "BUY",
                "1",
                "100",
                NOW,
            ),
        )

        raw.commit()
    finally:
        raw.close()

    with pytest.raises(
        SQLiteLedgerRepositoryError,
        match="foreign key",
    ):
        SQLiteLedgerRepository.verify_database_file(
            backup
        )
