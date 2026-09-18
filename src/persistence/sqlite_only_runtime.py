from __future__ import annotations

from datetime import datetime, timezone

from src.data.market_data import (
    ExecutionQuality,
)
from src.execution.models import (
    Execution,
    ExecutionProfile,
    OrderIntent,
    OrderSide,
    PaperMode,
    Position,
    PositionSide,
    PositionStatus,
)
from src.persistence.sqlite_repository import (
    SQLiteLedgerRepository,
)


class SQLiteOnlyRuntimeCompositionError(ValueError):
    pass


def _datetime_from_text(value):
    if value is None:
        return None

    parsed = datetime.fromisoformat(
        str(value).replace(
            "Z",
            "+00:00",
        )
    )

    if parsed.tzinfo is None:
        raise SQLiteOnlyRuntimeCompositionError(
            "SQLite datetime must be timezone-aware"
        )

    return parsed.astimezone(
        timezone.utc
    )


class VolatilePositionStateStore:
    """
    In-memory RealisticPaperRuntime state-store adapter.

    It implements the existing load_positions/save_positions interface
    without owning a path and without writing durable JSON state.
    """

    def __init__(
        self,
        positions=None,
    ):
        self._positions = dict(
            positions or {}
        )

    def load_positions(self):
        return dict(
            self._positions
        )

    def save_positions(
        self,
        positions,
    ):
        self._positions = dict(
            positions
        )


class SQLiteOpenPositionLoader:
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

    def load_positions(self):
        rows = self.repository.connection.execute(
            """
            SELECT *
            FROM positions
            WHERE status = 'OPEN'
            ORDER BY asset_id, position_id
            """
        ).fetchall()

        positions = {}

        for row in rows:
            asset_id = str(
                row["asset_id"]
            )

            if asset_id in positions:
                raise SQLiteOnlyRuntimeCompositionError(
                    "multiple OPEN positions for one asset"
                )

            if (
                row["execution_profile"]
                != ExecutionProfile.REALISTIC_V2.value
            ):
                raise SQLiteOnlyRuntimeCompositionError(
                    "restored position must be REALISTIC_V2"
                )

            position = Position(
                position_id=str(
                    row["position_id"]
                ),
                asset_id=asset_id,
                side=PositionSide(
                    row["side"]
                ),
                quantity=float(
                    row["quantity_native"]
                ),
                entry_execution_id=str(
                    row[
                        "entry_execution_id"
                    ]
                ),
                entry_price=float(
                    row[
                        "entry_price_native"
                    ]
                ),
                stop_loss=(
                    None
                    if row[
                        "stop_loss_native"
                    ]
                    is None
                    else float(
                        row[
                            "stop_loss_native"
                        ]
                    )
                ),
                take_profit=(
                    None
                    if row[
                        "take_profit_native"
                    ]
                    is None
                    else float(
                        row[
                            "take_profit_native"
                        ]
                    )
                ),
                opened_at=_datetime_from_text(
                    row[
                        "opened_at_utc"
                    ]
                ),
                short_mechanism=(
                    row[
                        "short_mechanism"
                    ]
                ),
                short_financing_model=(
                    row[
                        "short_financing_model"
                    ]
                ),
                execution_profile=(
                    ExecutionProfile.REALISTIC_V2
                ),
                execution_quality_at_entry=(
                    ExecutionQuality(
                        row[
                            "execution_quality_at_entry"
                        ]
                    )
                ),
                status=PositionStatus(
                    row["status"]
                ),
                closed_at=_datetime_from_text(
                    row[
                        "closed_at_utc"
                    ]
                ),
                exit_execution_id=(
                    row[
                        "exit_execution_id"
                    ]
                ),
                exit_price=(
                    None
                    if row[
                        "exit_price_native"
                    ]
                    is None
                    else float(
                        row[
                            "exit_price_native"
                        ]
                    )
                ),
                pending_exit_reason=None,
                pending_since=None,
            )

            positions[
                asset_id
            ] = position

        return positions


class SQLiteEntryExecutionResolver:
    """
    Replacement for JournalEntryExecutionResolver in SQLite-only mode.

    Returns the persisted ENTRY execution needed by realized accounting
    after process restart.
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

    def __call__(
        self,
        *,
        asset_id,
        position,
        entry_execution_id,
    ):
        asset_id = str(
            asset_id
        )
        entry_execution_id = str(
            entry_execution_id
        )

        row = self.repository.connection.execute(
            """
            SELECT
                e.*,
                o.intent AS order_intent,
                o.status AS order_status,
                o.paper_mode AS order_paper_mode
            FROM executions AS e
            JOIN orders AS o
              ON o.order_id = e.order_id
            WHERE e.execution_id = ?
            """,
            (
                entry_execution_id,
            ),
        ).fetchone()

        if row is None:
            return None

        if str(
            row["asset_id"]
        ) != asset_id:
            raise SQLiteOnlyRuntimeCompositionError(
                "ENTRY execution asset mismatch"
            )

        if str(
            row["order_intent"]
        ) != OrderIntent.ENTRY.value:
            raise SQLiteOnlyRuntimeCompositionError(
                "persisted execution is not ENTRY"
            )

        if str(
            row["order_status"]
        ) != "FILLED":
            raise SQLiteOnlyRuntimeCompositionError(
                "persisted ENTRY is not FILLED"
            )

        position_asset = str(
            getattr(
                position,
                "asset_id",
                "",
            )
        )

        if position_asset != asset_id:
            raise SQLiteOnlyRuntimeCompositionError(
                "position asset mismatch"
            )

        position_entry_id = str(
            getattr(
                position,
                "entry_execution_id",
                "",
            )
        )

        if position_entry_id != entry_execution_id:
            raise SQLiteOnlyRuntimeCompositionError(
                "position entry execution mismatch"
            )

        return Execution(
            execution_id=str(
                row["execution_id"]
            ),
            order_id=str(
                row["order_id"]
            ),
            asset_id=asset_id,
            side=OrderSide(
                row["side"]
            ),
            quantity=float(
                row[
                    "quantity_native"
                ]
            ),
            reference_price=float(
                row[
                    "reference_price_native"
                ]
            ),
            execution_price=float(
                row[
                    "execution_price_native"
                ]
            ),
            bid=float(
                row[
                    "bid_native"
                ]
            ),
            ask=float(
                row[
                    "ask_native"
                ]
            ),
            spread=float(
                row[
                    "spread_native"
                ]
            ),
            slippage=float(
                row[
                    "slippage_native"
                ]
            ),
            fee=float(
                row[
                    "fee_native"
                ]
            ),
            provider_timestamp=(
                _datetime_from_text(
                    row[
                        "provider_timestamp_utc"
                    ]
                )
            ),
            execution_timestamp=(
                _datetime_from_text(
                    row[
                        "execution_timestamp_utc"
                    ]
                )
            ),
            data_quality=str(
                row[
                    "data_quality"
                ]
            ),
            execution_quality=(
                ExecutionQuality(
                    row[
                        "execution_quality"
                    ]
                )
            ),
            session_quality=str(
                row[
                    "session_quality"
                ]
            ),
            paper_mode=PaperMode(
                row[
                    "order_paper_mode"
                ]
            ),
            short_label=None,
            trigger_reason=None,
            pending_reason=None,
            execution_reason="FILLED",
            labels=(),
            config_hash=str(
                row[
                    "config_hash"
                ]
            ),
        )


def assert_sqlite_only_components(
    *,
    state_store,
    broker,
):
    if not isinstance(
        state_store,
        VolatilePositionStateStore,
    ):
        raise SQLiteOnlyRuntimeCompositionError(
            "SQLite-only mode requires volatile state_store"
        )

    if hasattr(
        state_store,
        "path",
    ):
        raise SQLiteOnlyRuntimeCompositionError(
            "volatile state_store must not own a durable path"
        )

    if broker is None:
        raise SQLiteOnlyRuntimeCompositionError(
            "broker is required"
        )

    if getattr(
        broker,
        "execution_journal",
        None,
    ) is not None:
        raise SQLiteOnlyRuntimeCompositionError(
            "SQLite-only mode requires execution_journal=None"
        )
