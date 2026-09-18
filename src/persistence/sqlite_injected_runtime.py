from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.persistence.sqlite_repository import (
    SQLiteLedgerRepository,
)
from src.persistence.sqlite_runtime_adapter import (
    SQLiteRuntimePersistenceAdapter,
)
from src.persistence.sqlite_trade_cycle import (
    SQLiteTradeCycleCoordinator,
)


class SQLiteInjectedRuntimeError(ValueError):
    pass


def _required_text(value, field_name):
    if value is None:
        raise SQLiteInjectedRuntimeError(
            f"{field_name} is required"
        )

    result = str(value).strip()

    if not result:
        raise SQLiteInjectedRuntimeError(
            f"{field_name} is required"
        )

    return result


@dataclass(frozen=True)
class InjectedCycleWrite:
    intent: str
    processed_timestamp_utc: str
    updated_at_utc: str
    order: dict | None = None
    execution: dict | None = None
    position: dict | None = None
    reconciliation_event_id: str | None = None
    trade: dict | None = None
    portfolio_transaction: dict | None = None


@dataclass(frozen=True)
class SQLiteInjectedRunResult:
    runtime_result: object | None
    persisted: bool
    blocked_by_halt: bool
    asset_id: str


class SQLiteInjectedRuntime:
    """
    Explicit opt-in Phase 13 A.16 runtime persistence mode.

    This wrapper is intentionally separate from the default runtime path.
    It accepts exactly one asset per run in A.16.

    Safety:
    - the real data/live/trading.db path is rejected,
    - persistent HALT blocks assets without an existing OPEN position,
    - an existing OPEN position is still allowed to run for EXIT safety,
    - the wrapped runtime is snapshotted before execution and restored
      if SQLite persistence fails,
    - no JSON/JSONL persistence is performed by this wrapper.

    The caller is responsible for constructing the wrapped runtime
    without legacy durable writers.
    """

    def __init__(
        self,
        *,
        runtime,
        database_path,
        live_database_path,
        cycle_mapper,
        snapshot_provider,
        restore_snapshot,
    ):
        if runtime is None:
            raise TypeError(
                "runtime is required"
            )

        if not callable(cycle_mapper):
            raise TypeError(
                "cycle_mapper must be callable"
            )

        if not callable(snapshot_provider):
            raise TypeError(
                "snapshot_provider must be callable"
            )

        if not callable(restore_snapshot):
            raise TypeError(
                "restore_snapshot must be callable"
            )

        database_path = Path(
            database_path
        ).resolve()

        live_database_path = Path(
            live_database_path
        ).resolve()

        if database_path == live_database_path:
            raise SQLiteInjectedRuntimeError(
                "live SQLite database path is forbidden in A.16"
            )

        if not database_path.exists():
            raise SQLiteInjectedRuntimeError(
                "injected SQLite database must already exist"
            )

        self.runtime = runtime
        self.database_path = database_path
        self.live_database_path = live_database_path
        self.cycle_mapper = cycle_mapper
        self.snapshot_provider = snapshot_provider
        self.restore_snapshot = restore_snapshot

        self.repository = (
            SQLiteLedgerRepository.open_writer(
                database_path
            )
        )

        self.runtime_adapter = (
            SQLiteRuntimePersistenceAdapter(
                self.repository
            )
        )

        self.trade_cycle = (
            SQLiteTradeCycleCoordinator(
                self.repository
            )
        )

    def close(self):
        self.repository.close()

    def _open_assets(self):
        rows = self.repository.connection.execute(
            """
            SELECT asset_id
            FROM positions
            WHERE status = 'OPEN'
            """
        ).fetchall()

        return {
            str(row["asset_id"])
            for row in rows
        }

    def _halt_blocks_asset(
        self,
        asset_id,
    ):
        state = self.repository.read_system_state()

        if state is None:
            raise SQLiteInjectedRuntimeError(
                "system_state is required"
            )

        if not bool(state["halted"]):
            return False

        return (
            asset_id
            not in self._open_assets()
        )

    def _persist_write(
        self,
        write,
    ):
        if not isinstance(
            write,
            InjectedCycleWrite,
        ):
            raise SQLiteInjectedRuntimeError(
                "cycle_mapper must return InjectedCycleWrite"
            )

        intent = _required_text(
            write.intent,
            "write.intent",
        ).upper()

        if intent == "ENTRY":
            return (
                self.runtime_adapter
                .persist_execution_cycle(
                    processed_timestamp_utc=(
                        write
                        .processed_timestamp_utc
                    ),
                    updated_at_utc=(
                        write.updated_at_utc
                    ),
                    order=write.order,
                    execution=write.execution,
                    position=write.position,
                )
            )

        if intent == "EXIT":
            return (
                self.trade_cycle
                .persist_exit_and_settle_cycle(
                    processed_timestamp_utc=(
                        write
                        .processed_timestamp_utc
                    ),
                    updated_at_utc=(
                        write.updated_at_utc
                    ),
                    reconciliation_event_id=(
                        write
                        .reconciliation_event_id
                    ),
                    order=write.order,
                    execution=write.execution,
                    closed_position=write.position,
                    trade=write.trade,
                    portfolio_transaction=(
                        write
                        .portfolio_transaction
                    ),
                )
            )

        if intent == "NOOP":
            return None

        raise SQLiteInjectedRuntimeError(
            "write.intent must be ENTRY, EXIT or NOOP"
        )

    def run_cycle(
        self,
        asset_ids,
    ):
        asset_ids = tuple(
            str(value)
            for value in asset_ids
        )

        if len(asset_ids) != 1:
            raise SQLiteInjectedRuntimeError(
                "A.16 requires exactly one asset per run_cycle"
            )

        asset_id = _required_text(
            asset_ids[0],
            "asset_id",
        )

        if self._halt_blocks_asset(
            asset_id
        ):
            return SQLiteInjectedRunResult(
                runtime_result=None,
                persisted=False,
                blocked_by_halt=True,
                asset_id=asset_id,
            )

        snapshot = self.snapshot_provider()

        try:
            runtime_result = (
                self.runtime.run_cycle(
                    (asset_id,)
                )
            )

            write = self.cycle_mapper(
                asset_id=asset_id,
                runtime_result=runtime_result,
            )

            self._persist_write(
                write
            )

            persisted = (
                _required_text(
                    write.intent,
                    "write.intent",
                ).upper()
                != "NOOP"
            )
        except Exception:
            self.restore_snapshot(
                snapshot
            )
            raise

        return SQLiteInjectedRunResult(
            runtime_result=runtime_result,
            persisted=persisted,
            blocked_by_halt=False,
            asset_id=asset_id,
        )
