from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from src.persistence.sqlite_repository import (
    SQLiteLedgerRepository,
    SQLiteLedgerRepositoryError,
)


class SQLiteFinancialUnitOfWorkError(ValueError):
    pass


def _required_text(value, field_name):
    if value is None:
        raise SQLiteFinancialUnitOfWorkError(
            f"{field_name} is required"
        )

    result = str(value).strip()

    if not result:
        raise SQLiteFinancialUnitOfWorkError(
            f"{field_name} is required"
        )

    return result


def _decimal(value, field_name):
    try:
        result = Decimal(str(value))
    except (
        InvalidOperation,
        TypeError,
        ValueError,
    ) as exc:
        raise SQLiteFinancialUnitOfWorkError(
            f"{field_name} must be a finite decimal"
        ) from exc

    if not result.is_finite():
        raise SQLiteFinancialUnitOfWorkError(
            f"{field_name} must be a finite decimal"
        )

    return result


def _decimal_text(value):
    value = _decimal(
        value,
        "decimal value",
    )

    text = format(
        value,
        "f",
    )

    if "." in text:
        text = text.rstrip("0").rstrip(".")

    if text in ("", "-0"):
        return "0"

    return text


@dataclass(frozen=True)
class SQLiteFinancialSettlementResult:
    trade_created: bool
    transaction_created: bool
    cash_balance_pln: Decimal
    cash_reconciliation_matches: bool
    realized_reconciliation_matches: bool
    processed_timestamp_utc: str


class SQLiteFinancialUnitOfWork:
    """
    Phase 13 A.12 realized-financial transaction boundary.

    One atomic settlement contains:
    - realized trade,
    - REALIZED_PNL portfolio transaction,
    - settled cash mutation,
    - processed timestamp,
    - cash and realized-PnL reconciliation.

    The unit is deliberately not wired to production runtime in A.12.
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
            raise SQLiteFinancialUnitOfWorkError(
                "financial unit of work requires writable repository"
            )

        self.repository = repository

    def _validate_linkage(
        self,
        *,
        trade,
        portfolio_transaction,
    ):
        if not isinstance(trade, dict):
            raise SQLiteFinancialUnitOfWorkError(
                "trade must be a mapping"
            )

        if not isinstance(
            portfolio_transaction,
            dict,
        ):
            raise SQLiteFinancialUnitOfWorkError(
                "portfolio_transaction must be a mapping"
            )

        trade_id = _required_text(
            trade.get("trade_id"),
            "trade.trade_id",
        )

        transaction_id = _required_text(
            portfolio_transaction.get(
                "transaction_id"
            ),
            "portfolio_transaction.transaction_id",
        )

        transaction_type = _required_text(
            portfolio_transaction.get(
                "transaction_type"
            ),
            "portfolio_transaction.transaction_type",
        ).upper()

        if transaction_type != "REALIZED_PNL":
            raise SQLiteFinancialUnitOfWorkError(
                "portfolio transaction must be REALIZED_PNL"
            )

        reference_type = _required_text(
            portfolio_transaction.get(
                "reference_type"
            ),
            "portfolio_transaction.reference_type",
        ).upper()

        if reference_type != "TRADE":
            raise SQLiteFinancialUnitOfWorkError(
                "portfolio transaction reference_type must be TRADE"
            )

        reference_id = _required_text(
            portfolio_transaction.get(
                "reference_id"
            ),
            "portfolio_transaction.reference_id",
        )

        if reference_id != trade_id:
            raise SQLiteFinancialUnitOfWorkError(
                "portfolio transaction reference_id must equal trade_id"
            )

        realized_transaction_id = _required_text(
            trade.get(
                "realized_transaction_id"
            ),
            "trade.realized_transaction_id",
        )

        if realized_transaction_id != transaction_id:
            raise SQLiteFinancialUnitOfWorkError(
                "trade realized_transaction_id must equal transaction_id"
            )

        trade_realized = _decimal(
            trade.get(
                "realized_pnl_pln"
            ),
            "trade.realized_pnl_pln",
        )

        ledger_realized = _decimal(
            portfolio_transaction.get(
                "amount_pln"
            ),
            "portfolio_transaction.amount_pln",
        )

        if trade_realized != ledger_realized:
            raise SQLiteFinancialUnitOfWorkError(
                "trade and ledger realized PnL must match exactly"
            )

        return ledger_realized

    def _update_cash_balance(
        self,
        *,
        amount_pln,
        updated_at_utc,
    ):
        if not self.repository.connection.in_transaction:
            raise SQLiteLedgerRepositoryError(
                "cash update requires active atomic_cycle"
            )

        state = self.repository.read_system_state()

        if state is None:
            raise SQLiteFinancialUnitOfWorkError(
                "system_state is required"
            )

        current_cash = _decimal(
            state["cash_balance_pln"],
            "system_state.cash_balance_pln",
        )

        new_cash = (
            current_cash
            + amount_pln
        )

        cursor = self.repository.connection.execute(
            """
            UPDATE system_state
            SET
                cash_balance_pln = ?,
                updated_at_utc = ?
            """,
            (
                _decimal_text(new_cash),
                updated_at_utc,
            ),
        )

        if cursor.rowcount != 1:
            raise SQLiteLedgerRepositoryError(
                "system_state cash update affected "
                + str(cursor.rowcount)
                + " rows"
            )

        return new_cash

    def settle_realized_inside_atomic_cycle(
        self,
        *,
        processed_timestamp_utc,
        updated_at_utc,
        trade,
        portfolio_transaction,
    ):
        if not self.repository.connection.in_transaction:
            raise SQLiteLedgerRepositoryError(
                "financial settlement requires active atomic_cycle"
            )

        processed_timestamp_utc = _required_text(
            processed_timestamp_utc,
            "processed_timestamp_utc",
        )
        updated_at_utc = _required_text(
            updated_at_utc,
            "updated_at_utc",
        )

        amount_pln = self._validate_linkage(
            trade=trade,
            portfolio_transaction=portfolio_transaction,
        )

        _, transaction_created = (
            self.repository
            .append_portfolio_transaction_idempotent(
                portfolio_transaction
            )
        )

        _, trade_created = (
            self.repository
            .append_trade_idempotent(
                trade
            )
        )

        if trade_created != transaction_created:
            raise SQLiteFinancialUnitOfWorkError(
                "trade and REALIZED_PNL idempotency state mismatch"
            )

        if transaction_created:
            cash_balance = self._update_cash_balance(
                amount_pln=amount_pln,
                updated_at_utc=updated_at_utc,
            )
        else:
            state = self.repository.read_system_state()
            if state is None:
                raise SQLiteFinancialUnitOfWorkError(
                    "system_state is required"
                )
            cash_balance = _decimal(
                state["cash_balance_pln"],
                "system_state.cash_balance_pln",
            )

        self.repository.set_last_processed_timestamp(
            processed_timestamp_utc=processed_timestamp_utc,
            updated_at_utc=updated_at_utc,
        )

        cash_reconciliation = self.repository.reconcile_cash()
        if not cash_reconciliation.matches:
            raise SQLiteLedgerRepositoryError(
                "RECONCILIATION_MISMATCH: cash"
            )

        realized_reconciliation = (
            self.repository.reconcile_realized_pnl()
        )
        if not realized_reconciliation["matches"]:
            raise SQLiteLedgerRepositoryError(
                "RECONCILIATION_MISMATCH: realized PnL"
            )

        return SQLiteFinancialSettlementResult(
            trade_created=bool(trade_created),
            transaction_created=bool(transaction_created),
            cash_balance_pln=cash_balance,
            cash_reconciliation_matches=True,
            realized_reconciliation_matches=True,
            processed_timestamp_utc=processed_timestamp_utc,
        )

    def settle_realized_cycle(
        self,
        *,
        processed_timestamp_utc,
        updated_at_utc,
        reconciliation_event_id,
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

        amount_pln = self._validate_linkage(
            trade=trade,
            portfolio_transaction=portfolio_transaction,
        )

        self.repository.reconcile_or_halt(
            updated_at_utc=updated_at_utc,
            event_id=reconciliation_event_id,
            event_timestamp_utc=updated_at_utc,
        )

        with self.repository.atomic_cycle():
            # The trade row has a foreign key to its realized
            # portfolio transaction, so persist REALIZED_PNL first.
            # The transaction itself may reference trade_id as an
            # audit identity without requiring the trade row to exist.
            _, transaction_created = (
                self.repository
                .append_portfolio_transaction_idempotent(
                    portfolio_transaction
                )
            )

            _, trade_created = (
                self.repository
                .append_trade_idempotent(
                    trade
                )
            )

            if trade_created != transaction_created:
                raise SQLiteFinancialUnitOfWorkError(
                    "trade and REALIZED_PNL idempotency state mismatch"
                )

            if transaction_created:
                cash_balance = (
                    self._update_cash_balance(
                        amount_pln=amount_pln,
                        updated_at_utc=updated_at_utc,
                    )
                )
            else:
                state = self.repository.read_system_state()

                if state is None:
                    raise SQLiteFinancialUnitOfWorkError(
                        "system_state is required"
                    )

                cash_balance = _decimal(
                    state["cash_balance_pln"],
                    "system_state.cash_balance_pln",
                )

            self.repository.set_last_processed_timestamp(
                processed_timestamp_utc=processed_timestamp_utc,
                updated_at_utc=updated_at_utc,
            )

            cash_reconciliation = (
                self.repository
                .reconcile_cash()
            )

            if not cash_reconciliation.matches:
                raise SQLiteLedgerRepositoryError(
                    "RECONCILIATION_MISMATCH: cash"
                )

            realized_reconciliation = (
                self.repository
                .reconcile_realized_pnl()
            )

            if not realized_reconciliation["matches"]:
                raise SQLiteLedgerRepositoryError(
                    "RECONCILIATION_MISMATCH: realized PnL"
                )

        return SQLiteFinancialSettlementResult(
            trade_created=bool(
                trade_created
            ),
            transaction_created=bool(
                transaction_created
            ),
            cash_balance_pln=cash_balance,
            cash_reconciliation_matches=True,
            realized_reconciliation_matches=True,
            processed_timestamp_utc=processed_timestamp_utc,
        )
