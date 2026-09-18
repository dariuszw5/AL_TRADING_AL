from __future__ import annotations

import hashlib
import json
import sqlite3

from contextlib import contextmanager
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterator, Mapping


SCHEMA_VERSION = 1
SCHEMA_MIGRATION_NAME = "phase13_trading_schema_v1"

DEFAULT_BUSY_TIMEOUT_MS = 5000

DEFAULT_SCHEMA_PATH = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "sql"
    / "phase13_trading_schema_v1.sql"
)


class SQLiteLedgerRepositoryError(RuntimeError):
    pass


class ReadOnlyRepositoryError(
    SQLiteLedgerRepositoryError
):
    pass


class IdempotencyConflictError(
    SQLiteLedgerRepositoryError
):
    pass


class SchemaVersionError(
    SQLiteLedgerRepositoryError
):
    pass


class ReconciliationMismatchError(
    SQLiteLedgerRepositoryError
):
    pass


@dataclass(frozen=True)
class CashReconciliationResult:
    ledger_cash_pln: Decimal
    state_cash_pln: Decimal
    matches: bool


_DECIMAL_COLUMNS = {
    "orders": {
        "quantity_native",
    },
    "executions": {
        "quantity_native",
        "reference_price_native",
        "execution_price_native",
        "bid_native",
        "ask_native",
        "spread_native",
        "slippage_native",
        "fee_native",
        "fee_pln",
        "fx_rate",
    },
    "positions": {
        "quantity_native",
        "entry_price_native",
        "exit_price_native",
        "stop_loss_native",
        "take_profit_native",
        "unrealized_pnl_native",
        "unrealized_pnl_pln",
    },
    "portfolio_transactions": {
        "amount_pln",
        "fx_rate",
    },
    "trades": {
        "quantity_native",
        "realized_pnl_native",
        "realized_pnl_pln",
        "fees_pln",
        "spread_cost_pln",
        "slippage_pln",
        "realized_fx_rate",
    },
    "equity_snapshots": {
        "cash_balance_pln",
        "equity_pln",
        "realized_pnl_pln",
        "unrealized_pnl_pln",
        "exposure_pln",
        "drawdown_pln",
        "drawdown_percent",
    },
    "asset_equity_snapshots": {
        "position_value_native",
        "position_value_pln",
        "unrealized_pnl_native",
        "unrealized_pnl_pln",
        "exposure_pln",
        "fx_rate",
    },
    "system_state": {
        "cash_balance_pln",
    },
}

_JSON_COLUMNS = {
    "raw_json",
    "decision_payload_json",
    "payload_json",
}


def _canonical_decimal(
    value: Any,
) -> str:
    try:
        decimal_value = Decimal(
            str(value)
        )
    except (
        InvalidOperation,
        ValueError,
        TypeError,
    ) as exc:
        raise SQLiteLedgerRepositoryError(
            f"Invalid decimal value: {value!r}"
        ) from exc

    if not decimal_value.is_finite():
        raise SQLiteLedgerRepositoryError(
            "Financial decimal must be finite"
        )

    if decimal_value == 0:
        return "0"

    result = format(
        decimal_value,
        "f",
    )

    if "." in result:
        result = result.rstrip("0").rstrip(".")

    return result


def _canonical_json(
    value: Any,
) -> str:
    if isinstance(
        value,
        str,
    ):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return value

        return json.dumps(
            parsed,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


class SQLiteLedgerRepository:
    def __init__(
        self,
        connection: sqlite3.Connection,
        *,
        database_path: Path,
        read_only: bool,
        busy_timeout_ms: int,
    ):
        self.connection = connection
        self.database_path = database_path
        self.read_only = bool(
            read_only
        )
        self.busy_timeout_ms = int(
            busy_timeout_ms
        )

        self.connection.row_factory = (
            sqlite3.Row
        )

    @classmethod
    def open_writer(
        cls,
        database_path,
        *,
        busy_timeout_ms=DEFAULT_BUSY_TIMEOUT_MS,
    ):
        path = Path(
            database_path
        )

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        connection = sqlite3.connect(
            str(path),
            isolation_level=None,
        )

        repository = cls(
            connection,
            database_path=path,
            read_only=False,
            busy_timeout_ms=busy_timeout_ms,
        )

        repository._configure_writer()

        return repository

    @classmethod
    def open_reader(
        cls,
        database_path,
        *,
        busy_timeout_ms=DEFAULT_BUSY_TIMEOUT_MS,
    ):
        path = Path(
            database_path
        ).resolve()

        if not path.exists():
            raise SQLiteLedgerRepositoryError(
                f"Database does not exist: {path}"
            )

        uri = (
            "file:"
            + path.as_posix()
            + "?mode=ro"
        )

        connection = sqlite3.connect(
            uri,
            uri=True,
            isolation_level=None,
        )

        repository = cls(
            connection,
            database_path=path,
            read_only=True,
            busy_timeout_ms=busy_timeout_ms,
        )

        repository._configure_reader()

        return repository

    def _configure_writer(
        self,
    ):
        self.connection.execute(
            "PRAGMA foreign_keys=ON"
        )

        self.connection.execute(
            "PRAGMA busy_timeout="
            + str(
                self.busy_timeout_ms
            )
        )

        journal_mode = (
            self.connection.execute(
                "PRAGMA journal_mode=WAL"
            )
            .fetchone()[0]
        )

        if (
            str(journal_mode).lower()
            != "wal"
        ):
            raise SQLiteLedgerRepositoryError(
                "WAL mode was not enabled"
            )

        self.connection.execute(
            "PRAGMA synchronous=FULL"
        )

    def _configure_reader(
        self,
    ):
        self.connection.execute(
            "PRAGMA foreign_keys=ON"
        )

        self.connection.execute(
            "PRAGMA busy_timeout="
            + str(
                self.busy_timeout_ms
            )
        )

        self.connection.execute(
            "PRAGMA query_only=ON"
        )

    def close(
        self,
    ):
        self.connection.close()

    def connection_policy(
        self,
    ):
        return {
            "journal_mode": str(
                self.connection.execute(
                    "PRAGMA journal_mode"
                )
                .fetchone()[0]
            ).lower(),
            "foreign_keys": int(
                self.connection.execute(
                    "PRAGMA foreign_keys"
                )
                .fetchone()[0]
            ),
            "synchronous": int(
                self.connection.execute(
                    "PRAGMA synchronous"
                )
                .fetchone()[0]
            ),
            "busy_timeout": int(
                self.connection.execute(
                    "PRAGMA busy_timeout"
                )
                .fetchone()[0]
            ),
            "query_only": int(
                self.connection.execute(
                    "PRAGMA query_only"
                )
                .fetchone()[0]
            ),
        }

    def initialize_schema(
        self,
        *,
        applied_at_utc,
        schema_path=DEFAULT_SCHEMA_PATH,
    ):
        self._require_writer()

        path = Path(
            schema_path
        )

        sql = path.read_text(
            encoding="utf-8-sig"
        )

        checksum = hashlib.sha256(
            sql.encode("utf-8")
        ).hexdigest()

        self.connection.executescript(
            sql
        )

        existing = self.connection.execute(
            """
            SELECT
                version,
                migration_name,
                checksum_sha256,
                applied_at_utc
            FROM schema_version
            WHERE version = ?
            """,
            (
                SCHEMA_VERSION,
            ),
        ).fetchone()

        if existing is None:
            self.connection.execute(
                """
                INSERT INTO schema_version (
                    version,
                    migration_name,
                    checksum_sha256,
                    applied_at_utc
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    SCHEMA_VERSION,
                    SCHEMA_MIGRATION_NAME,
                    checksum,
                    str(
                        applied_at_utc
                    ),
                ),
            )

        else:
            if (
                existing["migration_name"]
                != SCHEMA_MIGRATION_NAME
                or existing["checksum_sha256"]
                != checksum
            ):
                raise SchemaVersionError(
                    "Existing schema version "
                    "does not match approved "
                    "schema checksum"
                )

        return self.schema_version()

    def schema_version(
        self,
    ):
        row = self.connection.execute(
            """
            SELECT
                version,
                migration_name,
                checksum_sha256,
                applied_at_utc
            FROM schema_version
            WHERE version = ?
            """,
            (
                SCHEMA_VERSION,
            ),
        ).fetchone()

        if row is None:
            raise SchemaVersionError(
                "Schema version is not initialized"
            )

        return dict(
            row
        )

    @contextmanager
    def atomic_cycle(
        self,
    ) -> Iterator[
        "SQLiteLedgerRepository"
    ]:
        self._require_writer()

        if self.connection.in_transaction:
            raise SQLiteLedgerRepositoryError(
                "Nested atomic cycles "
                "are not supported"
            )

        self.connection.execute(
            "BEGIN IMMEDIATE"
        )

        try:
            yield self
        except BaseException:
            self.connection.rollback()
            raise
        else:
            self.connection.commit()

    def _require_writer(
        self,
    ):
        if self.read_only:
            raise ReadOnlyRepositoryError(
                "Repository is read-only"
            )

    def _require_transaction(
        self,
    ):
        self._require_writer()

        if not self.connection.in_transaction:
            raise SQLiteLedgerRepositoryError(
                "Financial write requires "
                "an active atomic_cycle"
            )

    def _normalize_payload(
        self,
        table,
        payload: Mapping[str, Any],
    ):
        normalized = dict(
            payload
        )

        for column in (
            _DECIMAL_COLUMNS.get(
                table,
                set(),
            )
        ):
            if (
                column in normalized
                and normalized[column]
                is not None
            ):
                normalized[column] = (
                    _canonical_decimal(
                        normalized[column]
                    )
                )

        for column in _JSON_COLUMNS:
            if (
                column in normalized
                and normalized[column]
                is not None
            ):
                normalized[column] = (
                    _canonical_json(
                        normalized[column]
                    )
                )

        return normalized

    def _table_columns(
        self,
        table,
    ):
        rows = self.connection.execute(
            f"PRAGMA table_info('{table}')"
        ).fetchall()

        if not rows:
            raise SQLiteLedgerRepositoryError(
                f"Unknown table: {table}"
            )

        return {
            row["name"]
            for row in rows
        }

    def _validate_columns(
        self,
        table,
        payload,
    ):
        allowed = self._table_columns(
            table
        )

        unknown = (
            set(payload)
            - allowed
        )

        if unknown:
            raise SQLiteLedgerRepositoryError(
                "Unknown columns for "
                f"{table}: "
                + ", ".join(
                    sorted(
                        unknown
                    )
                )
            )

    def _insert(
        self,
        table,
        payload,
    ):
        self._validate_columns(
            table,
            payload,
        )

        columns = list(
            payload.keys()
        )

        placeholders = ",".join(
            "?"
            for _ in columns
        )

        column_sql = ",".join(
            columns
        )

        values = [
            payload[column]
            for column in columns
        ]

        self.connection.execute(
            f"""
            INSERT INTO {table} (
                {column_sql}
            )
            VALUES (
                {placeholders}
            )
            """,
            values,
        )

    @staticmethod
    def _rows_match(
        existing,
        payload,
    ):
        for key, value in payload.items():
            if existing[key] != value:
                return False

        return True

    def get_order_by_client_order_id(
        self,
        client_order_id,
    ):
        row = self.connection.execute(
            """
            SELECT *
            FROM orders
            WHERE client_order_id = ?
            """,
            (
                str(
                    client_order_id
                ),
            ),
        ).fetchone()

        if row is None:
            return None

        return dict(
            row
        )

    def insert_order_idempotent(
        self,
        payload,
    ):
        self._require_transaction()

        normalized = self._normalize_payload(
            "orders",
            payload,
        )

        client_order_id = normalized[
            "client_order_id"
        ]

        existing = self.connection.execute(
            """
            SELECT *
            FROM orders
            WHERE client_order_id = ?
            """,
            (
                client_order_id,
            ),
        ).fetchone()

        if existing is not None:
            if (
                existing["order_id"]
                == normalized["order_id"]
                and existing["order_fingerprint"]
                == normalized["order_fingerprint"]
            ):
                return (
                    dict(existing),
                    False,
                )

            raise IdempotencyConflictError(
                "client_order_id "
                "idempotency conflict"
            )

        existing_order_id = (
            self.connection.execute(
                """
                SELECT *
                FROM orders
                WHERE order_id = ?
                """,
                (
                    normalized[
                        "order_id"
                    ],
                ),
            )
            .fetchone()
        )

        if existing_order_id is not None:
            raise IdempotencyConflictError(
                "order_id "
                "idempotency conflict"
            )

        self._insert(
            "orders",
            normalized,
        )

        row = self.connection.execute(
            """
            SELECT *
            FROM orders
            WHERE client_order_id = ?
            """,
            (
                client_order_id,
            ),
        ).fetchone()

        return (
            dict(row),
            True,
        )

    def insert_execution_idempotent(
        self,
        payload,
    ):
        self._require_transaction()

        normalized = self._normalize_payload(
            "executions",
            payload,
        )

        execution_id = normalized[
            "execution_id"
        ]

        existing = self.connection.execute(
            """
            SELECT *
            FROM executions
            WHERE execution_id = ?
            """,
            (
                execution_id,
            ),
        ).fetchone()

        if existing is not None:
            if self._rows_match(
                existing,
                normalized,
            ):
                return (
                    dict(existing),
                    False,
                )

            raise IdempotencyConflictError(
                "execution_id "
                "idempotency conflict"
            )

        self._insert(
            "executions",
            normalized,
        )

        row = self.connection.execute(
            """
            SELECT *
            FROM executions
            WHERE execution_id = ?
            """,
            (
                execution_id,
            ),
        ).fetchone()

        return (
            dict(row),
            True,
        )

    def append_portfolio_transaction_idempotent(
        self,
        payload,
    ):
        self._require_transaction()

        normalized = self._normalize_payload(
            "portfolio_transactions",
            payload,
        )

        transaction_id = normalized[
            "transaction_id"
        ]

        existing = self.connection.execute(
            """
            SELECT *
            FROM portfolio_transactions
            WHERE transaction_id = ?
            """,
            (
                transaction_id,
            ),
        ).fetchone()

        if existing is not None:
            if self._rows_match(
                existing,
                normalized,
            ):
                return (
                    dict(existing),
                    False,
                )

            raise IdempotencyConflictError(
                "transaction_id "
                "idempotency conflict"
            )

        self._insert(
            "portfolio_transactions",
            normalized,
        )

        row = self.connection.execute(
            """
            SELECT *
            FROM portfolio_transactions
            WHERE transaction_id = ?
            """,
            (
                transaction_id,
            ),
        ).fetchone()

        return (
            dict(row),
            True,
        )

    def initialize_system_state(
        self,
        *,
        cash_balance_pln,
        updated_at_utc,
    ):
        self._require_transaction()

        canonical_cash = (
            _canonical_decimal(
                cash_balance_pln
            )
        )

        existing = self.connection.execute(
            """
            SELECT *
            FROM system_state
            WHERE state_id = 1
            """
        ).fetchone()

        if existing is not None:
            if (
                existing[
                    "cash_balance_pln"
                ]
                != canonical_cash
            ):
                raise IdempotencyConflictError(
                    "system_state cash "
                    "initialization conflict"
                )

            return dict(
                existing
            )

        self.connection.execute(
            """
            INSERT INTO system_state (
                state_id,
                cash_balance_pln,
                halted,
                halt_reason,
                last_processed_timestamp_utc,
                updated_at_utc
            )
            VALUES (
                1,
                ?,
                0,
                NULL,
                NULL,
                ?
            )
            """,
            (
                canonical_cash,
                str(
                    updated_at_utc
                ),
            ),
        )

        return self.read_system_state()

    def read_system_state(
        self,
    ):
        row = self.connection.execute(
            """
            SELECT *
            FROM system_state
            WHERE state_id = 1
            """
        ).fetchone()

        if row is None:
            return None

        return dict(
            row
        )


    def set_last_processed_timestamp(
        self,
        *,
        processed_timestamp_utc,
        updated_at_utc,
    ):
        self._require_transaction()

        timestamp = str(
            processed_timestamp_utc
        ).strip()

        if not timestamp:
            raise ValueError(
                "processed_timestamp_utc is required"
            )

        state = self.read_system_state()

        if state is None:
            raise SQLiteLedgerRepositoryError(
                "system_state missing"
            )

        self.connection.execute(
            """
            UPDATE system_state
            SET
                last_processed_timestamp_utc = ?,
                updated_at_utc = ?
            WHERE state_id = 1
            """,
            (
                timestamp,
                str(
                    updated_at_utc
                ),
            ),
        )

        return self.read_system_state()

    def read_last_processed_timestamp(
        self,
    ):
        state = self.read_system_state()

        if state is None:
            return None

        return state[
            "last_processed_timestamp_utc"
        ]

    def reconcile_cash(
        self,
    ):
        state = self.read_system_state()

        if state is None:
            raise ReconciliationMismatchError(
                "RECONCILIATION_MISMATCH: "
                "system_state missing"
            )

        ledger_cash = Decimal(
            "0"
        )

        rows = self.connection.execute(
            """
            SELECT amount_pln
            FROM portfolio_transactions
            ORDER BY booked_at_utc, transaction_id
            """
        ).fetchall()

        for row in rows:
            ledger_cash += Decimal(
                row["amount_pln"]
            )

        state_cash = Decimal(
            state["cash_balance_pln"]
        )

        result = CashReconciliationResult(
            ledger_cash_pln=ledger_cash,
            state_cash_pln=state_cash,
            matches=(
                ledger_cash
                == state_cash
            ),
        )

        if not result.matches:
            raise ReconciliationMismatchError(
                "RECONCILIATION_MISMATCH: "
                f"ledger={ledger_cash} "
                f"state={state_cash}"
            )

        return result


    def save_position_idempotent(
        self,
        payload,
    ):
        self._require_transaction()

        normalized = self._normalize_payload(
            "positions",
            payload,
        )

        position_id = normalized[
            "position_id"
        ]

        existing = self.connection.execute(
            """
            SELECT *
            FROM positions
            WHERE position_id = ?
            """,
            (
                position_id,
            ),
        ).fetchone()

        if existing is not None:
            if self._rows_match(
                existing,
                normalized,
            ):
                return (
                    dict(existing),
                    False,
                )

            raise IdempotencyConflictError(
                "position_id "
                "idempotency conflict"
            )

        try:
            self._insert(
                "positions",
                normalized,
            )
        except sqlite3.IntegrityError as exc:
            raise IdempotencyConflictError(
                "position persistence conflict"
            ) from exc

        row = self.connection.execute(
            """
            SELECT *
            FROM positions
            WHERE position_id = ?
            """,
            (
                position_id,
            ),
        ).fetchone()

        return (
            dict(row),
            True,
        )

    def append_trade_idempotent(
        self,
        payload,
    ):
        self._require_transaction()

        normalized = self._normalize_payload(
            "trades",
            payload,
        )

        trade_id = normalized[
            "trade_id"
        ]

        existing = self.connection.execute(
            """
            SELECT *
            FROM trades
            WHERE trade_id = ?
            """,
            (
                trade_id,
            ),
        ).fetchone()

        if existing is not None:
            if self._rows_match(
                existing,
                normalized,
            ):
                return (
                    dict(existing),
                    False,
                )

            raise IdempotencyConflictError(
                "trade_id "
                "idempotency conflict"
            )

        try:
            self._insert(
                "trades",
                normalized,
            )
        except sqlite3.IntegrityError as exc:
            raise IdempotencyConflictError(
                "trade persistence conflict"
            ) from exc

        row = self.connection.execute(
            """
            SELECT *
            FROM trades
            WHERE trade_id = ?
            """,
            (
                trade_id,
            ),
        ).fetchone()

        return (
            dict(row),
            True,
        )

    def append_system_event_idempotent(
        self,
        payload,
    ):
        self._require_transaction()

        normalized = self._normalize_payload(
            "system_events",
            payload,
        )

        event_id = normalized[
            "event_id"
        ]

        existing = self.connection.execute(
            """
            SELECT *
            FROM system_events
            WHERE event_id = ?
            """,
            (
                event_id,
            ),
        ).fetchone()

        if existing is not None:
            if self._rows_match(
                existing,
                normalized,
            ):
                return (
                    dict(existing),
                    False,
                )

            raise IdempotencyConflictError(
                "event_id "
                "idempotency conflict"
            )

        self._insert(
            "system_events",
            normalized,
        )

        row = self.connection.execute(
            """
            SELECT *
            FROM system_events
            WHERE event_id = ?
            """,
            (
                event_id,
            ),
        ).fetchone()

        return (
            dict(row),
            True,
        )

    def set_halt(
        self,
        *,
        reason,
        updated_at_utc,
        event_id,
        event_timestamp_utc,
        payload_json=None,
    ):
        self._require_transaction()

        reason_text = str(
            reason
        ).strip()

        if not reason_text:
            raise ValueError(
                "HALT reason is required"
            )

        state = self.read_system_state()

        if state is None:
            raise ReconciliationMismatchError(
                "RECONCILIATION_MISMATCH: "
                "system_state missing"
            )

        self.connection.execute(
            """
            UPDATE system_state
            SET
                halted = 1,
                halt_reason = ?,
                updated_at_utc = ?
            WHERE state_id = 1
            """,
            (
                reason_text,
                str(
                    updated_at_utc
                ),
            ),
        )

        event_payload = (
            payload_json
            if payload_json is not None
            else {
                "reason": reason_text,
            }
        )

        self.append_system_event_idempotent(
            {
                "event_id": str(
                    event_id
                ),
                "event_timestamp_utc": str(
                    event_timestamp_utc
                ),
                "level": "ERROR",
                "event_type": "SYSTEM_HALT",
                "asset_id": None,
                "correlation_id": None,
                "payload_json": event_payload,
            }
        )

        return self.read_system_state()

    def clear_halt_explicitly(
        self,
        *,
        reason,
        updated_at_utc,
        event_id,
        event_timestamp_utc,
    ):
        self._require_transaction()

        reason_text = str(
            reason
        ).strip()

        if not reason_text:
            raise ValueError(
                "Explicit HALT clear reason is required"
            )

        state = self.read_system_state()

        if state is None:
            raise SQLiteLedgerRepositoryError(
                "system_state missing"
            )

        self.connection.execute(
            """
            UPDATE system_state
            SET
                halted = 0,
                halt_reason = NULL,
                updated_at_utc = ?
            WHERE state_id = 1
            """,
            (
                str(
                    updated_at_utc
                ),
            ),
        )

        self.append_system_event_idempotent(
            {
                "event_id": str(
                    event_id
                ),
                "event_timestamp_utc": str(
                    event_timestamp_utc
                ),
                "level": "WARN",
                "event_type": "SYSTEM_HALT_CLEARED",
                "asset_id": None,
                "correlation_id": None,
                "payload_json": {
                    "reason": reason_text,
                },
            }
        )

        return self.read_system_state()

    def reconcile_realized_pnl(
        self,
    ):
        trades = self.connection.execute(
            """
            SELECT
                trade_id,
                realized_pnl_pln,
                realized_transaction_id
            FROM trades
            ORDER BY trade_id
            """
        ).fetchall()

        ledger_rows = self.connection.execute(
            """
            SELECT
                transaction_id,
                transaction_type,
                amount_pln
            FROM portfolio_transactions
            WHERE transaction_type = 'REALIZED_PNL'
            ORDER BY transaction_id
            """
        ).fetchall()

        ledger_by_id = {
            row["transaction_id"]: row
            for row in ledger_rows
        }

        trade_total = Decimal(
            "0"
        )

        linked_transaction_ids = set()

        for trade in trades:
            trade_amount = Decimal(
                trade[
                    "realized_pnl_pln"
                ]
            )

            trade_total += trade_amount

            transaction_id = trade[
                "realized_transaction_id"
            ]

            linked_transaction_ids.add(
                transaction_id
            )

            transaction = (
                ledger_by_id.get(
                    transaction_id
                )
            )

            if transaction is None:
                raise ReconciliationMismatchError(
                    "RECONCILIATION_MISMATCH: "
                    "trade has no REALIZED_PNL "
                    "ledger transaction"
                )

            ledger_amount = Decimal(
                transaction[
                    "amount_pln"
                ]
            )

            if ledger_amount != trade_amount:
                raise ReconciliationMismatchError(
                    "RECONCILIATION_MISMATCH: "
                    "trade realized PnL differs "
                    "from linked ledger amount"
                )

        ledger_ids = set(
            ledger_by_id
        )

        if linked_transaction_ids != ledger_ids:
            raise ReconciliationMismatchError(
                "RECONCILIATION_MISMATCH: "
                "unlinked REALIZED_PNL "
                "ledger transaction"
            )

        ledger_total = Decimal(
            "0"
        )

        for row in ledger_rows:
            ledger_total += Decimal(
                row["amount_pln"]
            )

        if trade_total != ledger_total:
            raise ReconciliationMismatchError(
                "RECONCILIATION_MISMATCH: "
                "aggregate realized PnL mismatch"
            )

        return {
            "trade_realized_pnl_pln": (
                trade_total
            ),
            "ledger_realized_pnl_pln": (
                ledger_total
            ),
            "trade_count": len(
                trades
            ),
            "ledger_transaction_count": len(
                ledger_rows
            ),
            "matches": True,
        }

    def reconcile_or_halt(
        self,
        *,
        updated_at_utc,
        event_id,
        event_timestamp_utc,
    ):
        try:
            cash = self.reconcile_cash()
            realized = (
                self.reconcile_realized_pnl()
            )

        except ReconciliationMismatchError as exc:
            with self.atomic_cycle():
                self.set_halt(
                    reason="RECONCILIATION_MISMATCH",
                    updated_at_utc=(
                        updated_at_utc
                    ),
                    event_id=event_id,
                    event_timestamp_utc=(
                        event_timestamp_utc
                    ),
                    payload_json={
                        "error": str(
                            exc
                        ),
                    },
                )

            raise

        return {
            "cash": cash,
            "realized": realized,
        }

    def count_rows(
        self,
        table,
    ):
        allowed = {
            "schema_version",
            "system_state",
            "orders",
            "executions",
            "positions",
            "portfolio_transactions",
            "trades",
            "equity_snapshots",
            "asset_equity_snapshots",
            "ai_decisions",
            "system_events",
        }

        if table not in allowed:
            raise SQLiteLedgerRepositoryError(
                f"Unsupported table: {table}"
            )

        return int(
            self.connection.execute(
                f"SELECT COUNT(*) FROM {table}"
            )
            .fetchone()[0]
        )
