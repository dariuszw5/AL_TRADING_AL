from __future__ import annotations

from dataclasses import dataclass

from src.persistence.sqlite_financial_unit_of_work import (
    SQLiteFinancialUnitOfWork,
)
from src.persistence.sqlite_repository import (
    SQLiteLedgerRepository,
)


class SQLiteTradeCycleError(ValueError):
    pass


def _required_text(value, field_name):
    if value is None:
        raise SQLiteTradeCycleError(
            f"{field_name} is required"
        )

    result = str(value).strip()

    if not result:
        raise SQLiteTradeCycleError(
            f"{field_name} is required"
        )

    return result


@dataclass(frozen=True)
class SQLiteExitSettlementResult:
    order_created: bool
    execution_created: bool
    position_closed: bool
    trade_created: bool
    transaction_created: bool
    cash_balance_pln: object
    processed_timestamp_utc: str


class SQLiteTradeCycleCoordinator:
    """
    Phase 13 A.14 temporary integration boundary.

    The EXIT cycle commits these effects in one SQLite transaction:
    order + execution + OPEN->CLOSED position + REALIZED_PNL +
    settled cash + processed timestamp.

    This coordinator is not wired to production runtime in A.14.
    """

    def __init__(self, repository):
        if not isinstance(
            repository,
            SQLiteLedgerRepository,
        ):
            raise TypeError(
                "repository must be SQLiteLedgerRepository"
            )

        policy = repository.connection_policy()

        if int(policy["query_only"]) != 0:
            raise SQLiteTradeCycleError(
                "trade cycle coordinator requires writable repository"
            )

        self.repository = repository
        self.financial_unit_of_work = SQLiteFinancialUnitOfWork(
            repository
        )

    def persist_exit_and_settle_cycle(
        self,
        *,
        processed_timestamp_utc,
        updated_at_utc,
        reconciliation_event_id,
        order,
        execution,
        closed_position,
        trade,
        portfolio_transaction,
    ):
        processed_timestamp_utc = _required_text(
            processed_timestamp_utc,
            "processed_timestamp_utc",
        )
        updated_at_utc = _required_text(
            updated_at_utc,
            "updated_at_utc",
        )
        reconciliation_event_id = _required_text(
            reconciliation_event_id,
            "reconciliation_event_id",
        )

        if not isinstance(order, dict):
            raise SQLiteTradeCycleError(
                "order must be a mapping"
            )

        intent = _required_text(
            order.get("intent"),
            "order.intent",
        ).upper()

        if intent != "EXIT":
            raise SQLiteTradeCycleError(
                "integrated trade cycle requires EXIT intent"
            )

        if not isinstance(execution, dict):
            raise SQLiteTradeCycleError(
                "execution must be a mapping"
            )

        if not isinstance(closed_position, dict):
            raise SQLiteTradeCycleError(
                "closed_position must be a mapping"
            )

        if (
            str(closed_position.get("status", "")).upper()
            != "CLOSED"
        ):
            raise SQLiteTradeCycleError(
                "closed_position status must be CLOSED"
            )

        self.repository.reconcile_or_halt(
            updated_at_utc=updated_at_utc,
            event_id=reconciliation_event_id,
            event_timestamp_utc=updated_at_utc,
        )

        with self.repository.atomic_cycle():
            _, order_created = (
                self.repository
                .insert_order_idempotent(
                    order
                )
            )

            _, execution_created = (
                self.repository
                .insert_execution_idempotent(
                    execution
                )
            )

            _, position_closed = (
                self.repository
                .close_position_idempotent(
                    closed_position
                )
            )

            financial = (
                self.financial_unit_of_work
                .settle_realized_inside_atomic_cycle(
                    processed_timestamp_utc=processed_timestamp_utc,
                    updated_at_utc=updated_at_utc,
                    trade=trade,
                    portfolio_transaction=portfolio_transaction,
                )
            )

        return SQLiteExitSettlementResult(
            order_created=bool(order_created),
            execution_created=bool(execution_created),
            position_closed=bool(position_closed),
            trade_created=financial.trade_created,
            transaction_created=financial.transaction_created,
            cash_balance_pln=financial.cash_balance_pln,
            processed_timestamp_utc=(
                financial.processed_timestamp_utc
            ),
        )
