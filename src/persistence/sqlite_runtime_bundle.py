from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.accounting.runtime_integration import (
    SnapshotCaptureDecisionProvider,
)
from src.execution.models import (
    PaperMode,
)
from src.execution.runtime import (
    RealisticPaperRuntime,
)
from src.persistence.sqlite_accounting_authority import (
    SQLiteCashAuthority,
    build_sqlite_phase09_accounting_runtime,
)
from src.persistence.sqlite_injected_runtime import (
    SQLiteInjectedRuntime,
    SQLiteInjectedRuntimeError,
)
from src.persistence.sqlite_only_runtime import (
    SQLiteOpenPositionLoader,
    VolatilePositionStateStore,
    assert_sqlite_only_components,
)
from src.persistence.sqlite_repository import (
    SQLiteLedgerRepository,
)


class SQLiteRuntimeBundleError(
    ValueError
):
    pass


@dataclass
class SQLiteOnlyRuntimeBundle:
    repository: SQLiteLedgerRepository
    state_store: VolatilePositionStateStore
    broker: object
    base_runtime: RealisticPaperRuntime
    accounting_runtime: object
    injected_runtime: SQLiteInjectedRuntime
    cash_authority: SQLiteCashAuthority

    def run_cycle(
        self,
        asset_ids,
    ):
        return self.injected_runtime.run_cycle(
            asset_ids
        )

    def close(self):
        try:
            self.injected_runtime.close()
        finally:
            self.repository.close()


def _restore_runtime_positions(
    *,
    runtime,
    state_store,
    snapshot,
):
    runtime.positions.clear()
    runtime.positions.update(
        snapshot
    )
    state_store.save_positions(
        snapshot
    )


def build_sqlite_only_runtime_bundle(
    *,
    database_path,
    live_database_path,
    market_data_service,
    market_session_service,
    broker,
    decision_provider,
    clock,
    paper_mode,
    accounting_bridge,
    fx_conversion_resolver,
    estimated_exit_fee_resolver,
    realized_quotes_resolver,
    cycle_mapper_factory,
):
    database_path = Path(
        database_path
    ).resolve()

    live_database_path = Path(
        live_database_path
    ).resolve()

    if database_path == live_database_path:
        raise SQLiteRuntimeBundleError(
            "live SQLite database path is forbidden"
        )

    if not database_path.exists():
        raise SQLiteRuntimeBundleError(
            "SQLite database must already exist"
        )

    if paper_mode is not PaperMode.REALISTIC_PAPER:
        raise SQLiteRuntimeBundleError(
            "SQLite-only bundle requires realistic_paper mode"
        )

    if not callable(
        cycle_mapper_factory
    ):
        raise TypeError(
            "cycle_mapper_factory must be callable"
        )

    repository = (
        SQLiteLedgerRepository.open_writer(
            database_path
        )
    )

    try:
        # Fail closed at startup before runtime construction.
        cash_authority = SQLiteCashAuthority(
            repository
        )
        cash_authority.current_cash_pln()

        restored_positions = (
            SQLiteOpenPositionLoader(
                repository
            )
            .load_positions()
        )

        state_store = (
            VolatilePositionStateStore(
                restored_positions
            )
        )

        assert_sqlite_only_components(
            state_store=state_store,
            broker=broker,
        )

        snapshot_capture = (
            SnapshotCaptureDecisionProvider(
                decision_provider
            )
        )

        base_runtime = RealisticPaperRuntime(
            market_data_service=market_data_service,
            market_session_service=market_session_service,
            broker=broker,
            decision_provider=snapshot_capture,
            clock=clock,
            paper_mode=paper_mode,
            state_store=state_store,
        )

        accounting_runtime = (
            build_sqlite_phase09_accounting_runtime(
                repository=repository,
                runtime=base_runtime,
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
            )
        )

        cycle_mapper = cycle_mapper_factory(
            repository
        )

        if not callable(
            cycle_mapper
        ):
            raise TypeError(
                "cycle_mapper_factory must return callable"
            )

        injected_runtime = SQLiteInjectedRuntime(
            runtime=accounting_runtime,
            database_path=database_path,
            live_database_path=live_database_path,
            repository=repository,
            cycle_mapper=cycle_mapper,
            snapshot_provider=(
                lambda: dict(
                    base_runtime.positions
                )
            ),
            restore_snapshot=(
                lambda snapshot: (
                    _restore_runtime_positions(
                        runtime=base_runtime,
                        state_store=state_store,
                        snapshot=snapshot,
                    )
                )
            ),
        )

        return SQLiteOnlyRuntimeBundle(
            repository=repository,
            state_store=state_store,
            broker=broker,
            base_runtime=base_runtime,
            accounting_runtime=accounting_runtime,
            injected_runtime=injected_runtime,
            cash_authority=cash_authority,
        )

    except Exception:
        repository.close()
        raise
