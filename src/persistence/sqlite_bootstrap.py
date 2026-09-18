from __future__ import annotations

from decimal import Decimal, InvalidOperation
from pathlib import Path

from src.persistence.sqlite_repository import (
    SQLiteLedgerRepository,
    SQLiteLedgerRepositoryError,
)


FRESH_BOOTSTRAP_HALT_REASON = (
    "FRESH_BOOTSTRAP_REQUIRES_EXPLICIT_ACTIVATION"
)


class FreshSQLiteBootstrapError(ValueError):
    pass


def _required_text(value, field_name):
    if value is None:
        raise FreshSQLiteBootstrapError(
            f"{field_name} is required"
        )

    result = str(value).strip()

    if not result:
        raise FreshSQLiteBootstrapError(
            f"{field_name} is required"
        )

    return result


def _initial_cash(value):
    try:
        result = Decimal(str(value))
    except (
        InvalidOperation,
        TypeError,
        ValueError,
    ) as exc:
        raise FreshSQLiteBootstrapError(
            "initial_cash_pln must be a finite non-negative decimal"
        ) from exc

    if not result.is_finite() or result < Decimal("0"):
        raise FreshSQLiteBootstrapError(
            "initial_cash_pln must be a finite non-negative decimal"
        )

    return result


def _cleanup_database_files(path):
    candidates = (
        path,
        Path(str(path) + "-wal"),
        Path(str(path) + "-shm"),
    )

    for candidate in candidates:
        try:
            if candidate.exists():
                candidate.unlink()
        except OSError:
            pass


def bootstrap_fresh_database(
    database_path,
    *,
    initial_cash_pln,
    bootstrap_id,
    created_at_utc,
):
    path = Path(database_path)

    if path.exists():
        raise FileExistsError(
            f"Fresh SQLite database already exists: {path}"
        )

    cash = _initial_cash(
        initial_cash_pln
    )

    bootstrap_id = _required_text(
        bootstrap_id,
        "bootstrap_id",
    )

    created_at_utc = _required_text(
        created_at_utc,
        "created_at_utc",
    )

    cash_text = format(
        cash,
        "f",
    )

    transaction_id = (
        "fresh-bootstrap:"
        + bootstrap_id
        + ":initial-cash"
    )

    halt_event_id = (
        "fresh-bootstrap:"
        + bootstrap_id
        + ":halt"
    )

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    repository = None

    try:
        repository = (
            SQLiteLedgerRepository
            .open_writer(
                path
            )
        )

        repository.initialize_schema(
            applied_at_utc=created_at_utc
        )

        with repository.atomic_cycle():
            repository.initialize_system_state(
                cash_balance_pln=cash_text,
                updated_at_utc=created_at_utc,
            )

            repository.append_portfolio_transaction_idempotent(
                {
                    "transaction_id": transaction_id,
                    "transaction_type": "INITIAL_CASH",
                    "amount_pln": cash_text,
                    "asset_id": None,
                    "reference_type": "FRESH_BOOTSTRAP",
                    "reference_id": bootstrap_id,
                    "booked_at_utc": created_at_utc,
                    "fx_pair": None,
                    "fx_path": None,
                    "fx_rate": None,
                    "fx_provider": None,
                    "fx_timestamp_utc": None,
                    "fx_quality": None,
                    "raw_json": {
                        "bootstrap_id": bootstrap_id,
                        "source": "EXPLICIT_INITIAL_CASH",
                        "legacy_state_imported": False,
                    },
                }
            )

            repository.set_halt(
                reason=FRESH_BOOTSTRAP_HALT_REASON,
                updated_at_utc=created_at_utc,
                event_id=halt_event_id,
                event_timestamp_utc=created_at_utc,
            )

            reconciliation = (
                repository.reconcile_cash()
            )

            if not reconciliation.matches:
                raise SQLiteLedgerRepositoryError(
                    "Fresh bootstrap cash reconciliation failed"
                )

        state = repository.read_system_state()

        if state is None:
            raise SQLiteLedgerRepositoryError(
                "Fresh bootstrap system_state missing"
            )

        if int(state["halted"]) != 1:
            raise SQLiteLedgerRepositoryError(
                "Fresh bootstrap must start halted"
            )

        if (
            state["halt_reason"]
            != FRESH_BOOTSTRAP_HALT_REASON
        ):
            raise SQLiteLedgerRepositoryError(
                "Fresh bootstrap HALT reason mismatch"
            )

        if (
            repository.read_last_processed_timestamp()
            is not None
        ):
            raise SQLiteLedgerRepositoryError(
                "Fresh bootstrap processed timestamp must be NULL"
            )

        for table_name in (
            "orders",
            "executions",
            "positions",
            "trades",
            "equity_snapshots",
            "asset_equity_snapshots",
            "ai_decisions",
        ):
            if repository.count_rows(table_name) != 0:
                raise SQLiteLedgerRepositoryError(
                    "Fresh bootstrap inherited trading state: "
                    + table_name
                )

        summary = {
            "database_path": str(path),
            "bootstrap_id": bootstrap_id,
            "cash_balance_pln": str(
                state["cash_balance_pln"]
            ),
            "halted": bool(
                state["halted"]
            ),
            "halt_reason": str(
                state["halt_reason"]
            ),
            "last_processed_timestamp_utc": (
                repository
                .read_last_processed_timestamp()
            ),
            "cash_reconciliation_matches": True,
            "legacy_state_imported": False,
        }

        repository.close()
        repository = None

        (
            SQLiteLedgerRepository
            .verify_database_file(
                path
            )
        )

        return summary

    except BaseException:
        if repository is not None:
            try:
                repository.close()
            except Exception:
                pass

        _cleanup_database_files(
            path
        )

        raise
