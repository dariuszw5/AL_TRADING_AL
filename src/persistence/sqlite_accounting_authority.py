from __future__ import annotations

from decimal import Decimal, InvalidOperation

from src.accounting.journal_entry_recovery import (
    JournalBackedPhase09AccountingRuntime,
)
from src.persistence.sqlite_only_runtime import (
    SQLiteEntryExecutionResolver,
)
from src.persistence.sqlite_repository import (
    ReconciliationMismatchError,
    SQLiteLedgerRepository,
)


class SQLiteAccountingAuthorityError(
    ValueError
):
    pass


class SQLiteCashAuthority:
    """
    Read current settled PLN cash from Phase 13 SQLite only.

    Cash is returned only when system_state and the portfolio transaction
    ledger reconcile exactly.
    """

    def __init__(
        self,
        repository,
    ):
        if not isinstance(
            repository,
            SQLiteLedgerRepository,
        ):
            raise TypeError(
                "repository must be SQLiteLedgerRepository"
            )

        self.repository = repository

    def current_cash_pln(self):
        try:
            reconciliation = (
                self.repository
                .reconcile_cash()
            )
        except ReconciliationMismatchError as exc:
            raise SQLiteAccountingAuthorityError(
                "cash reconciliation mismatch"
            ) from exc

        if not reconciliation.matches:
            raise SQLiteAccountingAuthorityError(
                "cash reconciliation mismatch"
            )

        state = (
            self.repository
            .read_system_state()
        )

        if state is None:
            raise SQLiteAccountingAuthorityError(
                "system_state is required"
            )

        try:
            cash = Decimal(
                str(
                    state[
                        "cash_balance_pln"
                    ]
                )
            )
        except (
            InvalidOperation,
            ValueError,
            TypeError,
        ) as exc:
            raise SQLiteAccountingAuthorityError(
                "cash_balance_pln must be decimal"
            ) from exc

        if not cash.is_finite():
            raise SQLiteAccountingAuthorityError(
                "cash_balance_pln must be finite"
            )

        return cash


def build_sqlite_phase09_accounting_runtime(
    *,
    repository,
    runtime,
    accounting_bridge,
    snapshot_capture,
    fx_conversion_resolver,
    estimated_exit_fee_resolver,
    realized_quotes_resolver,
):
    """
    Reuse the existing Phase 09 accounting implementation after restart,
    replacing only the legacy JSONL entry-execution fallback with the
    exact SQLite entry-execution resolver.
    """

    if not isinstance(
        repository,
        SQLiteLedgerRepository,
    ):
        raise TypeError(
            "repository must be SQLiteLedgerRepository"
        )

    return JournalBackedPhase09AccountingRuntime(
        runtime=runtime,
        accounting_bridge=accounting_bridge,
        snapshot_capture=snapshot_capture,
        fx_conversion_resolver=(
            fx_conversion_resolver
        ),
        estimated_exit_fee_resolver=(
            estimated_exit_fee_resolver
        ),
        realized_quotes_resolver=(
            realized_quotes_resolver
        ),
        entry_execution_resolver=(
            SQLiteEntryExecutionResolver(
                repository
            )
        ),
    )
