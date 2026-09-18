from decimal import Decimal

import pytest

from src.persistence.sqlite_bootstrap import (
    FreshSQLiteBootstrapError,
    bootstrap_fresh_database,
)
from src.persistence.sqlite_repository import (
    SQLiteLedgerRepository,
)


NOW = "2026-09-18T19:00:00.000000Z"
BOOTSTRAP_ID = "phase13-a8-test"


def test_fresh_bootstrap_creates_reconciled_initial_cash(tmp_path):
    path = tmp_path / "fresh.db"

    result = bootstrap_fresh_database(
        path,
        initial_cash_pln="1000.00",
        bootstrap_id=BOOTSTRAP_ID,
        created_at_utc=NOW,
    )

    assert path.exists()
    assert Decimal(result["cash_balance_pln"]) == Decimal("1000")
    assert result["cash_reconciliation_matches"] is True

    repo = SQLiteLedgerRepository.open_reader(path)

    try:
        state = repo.read_system_state()

        assert Decimal(state["cash_balance_pln"]) == Decimal("1000")
        assert repo.count_rows("portfolio_transactions") == 1

        row = repo.connection.execute(
            """
            SELECT
                transaction_type,
                amount_pln,
                reference_type,
                reference_id
            FROM portfolio_transactions
            """
        ).fetchone()

        assert row["transaction_type"] == "INITIAL_CASH"
        assert Decimal(row["amount_pln"]) == Decimal("1000")
        assert row["reference_type"] == "FRESH_BOOTSTRAP"
        assert row["reference_id"] == BOOTSTRAP_ID
    finally:
        repo.close()


def test_fresh_bootstrap_starts_halted(tmp_path):
    path = tmp_path / "halted.db"

    bootstrap_fresh_database(
        path,
        initial_cash_pln="1000",
        bootstrap_id=BOOTSTRAP_ID,
        created_at_utc=NOW,
    )

    repo = SQLiteLedgerRepository.open_reader(path)

    try:
        state = repo.read_system_state()

        assert state["halted"] == 1
        assert (
            state["halt_reason"]
            == "FRESH_BOOTSTRAP_REQUIRES_EXPLICIT_ACTIVATION"
        )

        assert repo.count_rows("system_events") == 1
    finally:
        repo.close()


def test_fresh_bootstrap_has_no_inherited_trading_state(tmp_path):
    path = tmp_path / "empty-trading-state.db"

    bootstrap_fresh_database(
        path,
        initial_cash_pln="0",
        bootstrap_id=BOOTSTRAP_ID,
        created_at_utc=NOW,
    )

    repo = SQLiteLedgerRepository.open_reader(path)

    try:
        assert repo.count_rows("orders") == 0
        assert repo.count_rows("executions") == 0
        assert repo.count_rows("positions") == 0
        assert repo.count_rows("trades") == 0
        assert repo.count_rows("equity_snapshots") == 0
        assert repo.count_rows("asset_equity_snapshots") == 0
        assert repo.count_rows("ai_decisions") == 0

        assert repo.read_last_processed_timestamp() is None
    finally:
        repo.close()


def test_fresh_bootstrap_is_visible_to_read_only_reader(tmp_path):
    path = tmp_path / "reader.db"

    bootstrap_fresh_database(
        path,
        initial_cash_pln="2500.50",
        bootstrap_id=BOOTSTRAP_ID,
        created_at_utc=NOW,
    )

    reader = SQLiteLedgerRepository.open_reader(path)

    try:
        state = reader.read_system_state()

        assert Decimal(state["cash_balance_pln"]) == Decimal("2500.50")
        assert state["halted"] == 1

        reconciliation = reader.reconcile_cash()
        assert reconciliation.matches is True
    finally:
        reader.close()


def test_fresh_bootstrap_backup_restore_preserves_state(tmp_path):
    path = tmp_path / "source.db"
    backup = tmp_path / "backup.db"
    restored = tmp_path / "restored.db"

    bootstrap_fresh_database(
        path,
        initial_cash_pln="777.25",
        bootstrap_id=BOOTSTRAP_ID,
        created_at_utc=NOW,
    )

    writer = SQLiteLedgerRepository.open_writer(path)

    try:
        writer.backup_to(backup)
    finally:
        writer.close()

    restored_repo = SQLiteLedgerRepository.restore_from_backup(
        backup,
        restored,
    )

    try:
        state = restored_repo.read_system_state()

        assert Decimal(state["cash_balance_pln"]) == Decimal("777.25")
        assert state["halted"] == 1
        assert restored_repo.read_last_processed_timestamp() is None
        assert restored_repo.reconcile_cash().matches is True
    finally:
        restored_repo.close()


def test_fresh_bootstrap_refuses_existing_database(tmp_path):
    path = tmp_path / "existing.db"
    path.write_bytes(b"do-not-touch")

    before = path.read_bytes()

    with pytest.raises(
        FileExistsError,
        match="already exists",
    ):
        bootstrap_fresh_database(
            path,
            initial_cash_pln="1000",
            bootstrap_id=BOOTSTRAP_ID,
            created_at_utc=NOW,
        )

    assert path.read_bytes() == before


@pytest.mark.parametrize(
    "initial_cash_pln",
    [
        "-0.01",
        "NaN",
        "Infinity",
    ],
)
def test_fresh_bootstrap_rejects_invalid_initial_cash(
    tmp_path,
    initial_cash_pln,
):
    path = tmp_path / "invalid.db"

    with pytest.raises(
        FreshSQLiteBootstrapError,
        match="initial_cash_pln",
    ):
        bootstrap_fresh_database(
            path,
            initial_cash_pln=initial_cash_pln,
            bootstrap_id=BOOTSTRAP_ID,
            created_at_utc=NOW,
        )

    assert path.exists() is False


def test_fresh_bootstrap_failure_removes_partial_database(
    tmp_path,
    monkeypatch,
):
    path = tmp_path / "partial.db"

    original = SQLiteLedgerRepository.set_halt

    def fail_set_halt(self, **kwargs):
        raise RuntimeError("forced bootstrap failure")

    monkeypatch.setattr(
        SQLiteLedgerRepository,
        "set_halt",
        fail_set_halt,
    )

    with pytest.raises(
        RuntimeError,
        match="forced bootstrap failure",
    ):
        bootstrap_fresh_database(
            path,
            initial_cash_pln="1000",
            bootstrap_id=BOOTSTRAP_ID,
            created_at_utc=NOW,
        )

    monkeypatch.setattr(
        SQLiteLedgerRepository,
        "set_halt",
        original,
    )

    assert path.exists() is False
    assert (tmp_path / "partial.db-wal").exists() is False
    assert (tmp_path / "partial.db-shm").exists() is False
