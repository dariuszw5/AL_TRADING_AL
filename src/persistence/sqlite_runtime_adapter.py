from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from src.persistence.sqlite_repository import (
    SQLiteLedgerRepository,
)


class SQLiteRuntimePersistenceError(ValueError):
    pass


class SQLiteRuntimePersistenceHaltedError(
    SQLiteRuntimePersistenceError
):
    pass


def _required_text(value, field_name):
    if value is None:
        raise SQLiteRuntimePersistenceError(
            f"{field_name} is required"
        )

    result = str(value).strip()

    if not result:
        raise SQLiteRuntimePersistenceError(
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
        raise SQLiteRuntimePersistenceError(
            f"{field_name} must be a finite decimal"
        ) from exc

    if not result.is_finite():
        raise SQLiteRuntimePersistenceError(
            f"{field_name} must be a finite decimal"
        )

    return result


@dataclass(frozen=True)
class SQLiteRuntimeStartupSnapshot:
    halted: bool
    halt_reason: str | None
    cash_balance_pln: Decimal
    last_processed_timestamp_utc: str | None


@dataclass(frozen=True)
class SQLiteRuntimeCyclePersistResult:
    order_created: bool | None
    execution_created: bool | None
    position_created: bool | None
    processed_timestamp_utc: str


class SQLiteRuntimePersistenceAdapter:
    """
    Phase 13 A.11 non-financial runtime persistence boundary.

    Scope:
    - reads persistent startup HALT/cash/timestamp,
    - persists order/execution/position/timestamp atomically,
    - blocks new ENTRY persistence while SQLite system_state is HALTED,
    - allows EXIT persistence while HALTED,
    - does not persist trades or portfolio transactions yet.

    A.11 intentionally does not change realized-PnL or cash semantics.
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
            raise SQLiteRuntimePersistenceError(
                "runtime adapter requires writable repository"
            )

        self.repository = repository

    def startup_snapshot(self):
        state = self.repository.read_system_state()

        if state is None:
            raise SQLiteRuntimePersistenceError(
                "system_state is required"
            )

        cash = _decimal(
            state["cash_balance_pln"],
            "cash_balance_pln",
        )

        return SQLiteRuntimeStartupSnapshot(
            halted=bool(state["halted"]),
            halt_reason=state["halt_reason"],
            cash_balance_pln=cash,
            last_processed_timestamp_utc=(
                self.repository
                .read_last_processed_timestamp()
            ),
        )

    def _validate_halt_for_order(self, order):
        if order is None:
            return

        if not isinstance(order, dict):
            raise SQLiteRuntimePersistenceError(
                "order must be a mapping"
            )

        intent = _required_text(
            order.get("intent"),
            "order.intent",
        ).upper()

        if intent != "ENTRY":
            return

        snapshot = self.startup_snapshot()

        if snapshot.halted:
            reason = (
                snapshot.halt_reason
                or "UNSPECIFIED"
            )

            raise SQLiteRuntimePersistenceHaltedError(
                "HALTED: new ENTRY persistence blocked: "
                + reason
            )

    def persist_execution_cycle(
        self,
        *,
        processed_timestamp_utc,
        updated_at_utc,
        order=None,
        execution=None,
        position=None,
    ):
        processed_timestamp_utc = _required_text(
            processed_timestamp_utc,
            "processed_timestamp_utc",
        )

        updated_at_utc = _required_text(
            updated_at_utc,
            "updated_at_utc",
        )

        self._validate_halt_for_order(
            order
        )

        order_created = None
        execution_created = None
        position_created = None

        with self.repository.atomic_cycle():
            if order is not None:
                _, order_created = (
                    self.repository
                    .insert_order_idempotent(
                        order
                    )
                )

            if execution is not None:
                _, execution_created = (
                    self.repository
                    .insert_execution_idempotent(
                        execution
                    )
                )

            if position is not None:
                _, position_created = (
                    self.repository
                    .save_position_idempotent(
                        position
                    )
                )

            self.repository.set_last_processed_timestamp(
                processed_timestamp_utc=(
                    processed_timestamp_utc
                ),
                updated_at_utc=updated_at_utc,
            )

        return SQLiteRuntimeCyclePersistResult(
            order_created=order_created,
            execution_created=execution_created,
            position_created=position_created,
            processed_timestamp_utc=(
                processed_timestamp_utc
            ),
        )
