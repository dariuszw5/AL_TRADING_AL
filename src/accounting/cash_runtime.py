from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType

from src.accounting.cash_ledger import (
    Phase11CashLedger,
)
from src.accounting.production_startup import (
    Phase10ProductionRuntimeBundle,
    wire_phase10_production_runtime,
)
from src.accounting.realized_persistence import (
    PersistingAccountingRuntime,
    RealizedAccountingJournal,
)
from src.accounting.runtime_integration import (
    PORTFOLIO_PARTIAL_ACCOUNTING_BLOCKED,
    RuntimeAccountingCycleResult,
)


class Phase11CashRuntimeError(
    ValueError
):
    pass


def reconcile_cash_ledger(
    *,
    cash_ledger,
    realized_journal,
):
    if not isinstance(
        cash_ledger,
        Phase11CashLedger,
    ):
        raise TypeError(
            "cash_ledger must be Phase11CashLedger"
        )

    if not isinstance(
        realized_journal,
        RealizedAccountingJournal,
    ):
        raise TypeError(
            "realized_journal must be RealizedAccountingJournal"
        )

    # Verifies the authoritative cash ledger even when no realized
    # records exist.
    cash_ledger.current_cash_pln()

    results = []

    for record in (
        realized_journal
        .read_records()
    ):
        results.append(
            cash_ledger
            .settle_from_realized_journal(
                realized_journal=(
                    realized_journal
                ),
                booking_key=(
                    record[
                        "booking_key"
                    ]
                ),
            )
        )

    return tuple(
        results
    )


class Phase11CashAccountingRuntime:
    """
    Controlled Phase 11 accounting wrapper.

    Order for a successful CLOSE:

    1. unchanged REALISTIC_V2 paper execution,
    2. Phase 09 realized accounting,
    3. Phase 10 realized booking persistence,
    4. Phase 11 settled-cash persistence,
    5. portfolio snapshot rebuilt from authoritative cash ledger.

    This wrapper does not implement buying power, capital reservation,
    margin, collateral or short-financing semantics.
    """

    def __init__(
        self,
        *,
        persisting_runtime,
        cash_ledger,
        realized_journal,
        portfolio_snapshot_builder,
    ):
        if persisting_runtime is None:
            raise TypeError(
                "persisting_runtime is required"
            )

        if not isinstance(
            cash_ledger,
            Phase11CashLedger,
        ):
            raise TypeError(
                "cash_ledger must be Phase11CashLedger"
            )

        if not isinstance(
            realized_journal,
            RealizedAccountingJournal,
        ):
            raise TypeError(
                "realized_journal must be RealizedAccountingJournal"
            )

        if (
            getattr(
                persisting_runtime,
                "journal",
                None,
            )
            is not realized_journal
        ):
            raise Phase11CashRuntimeError(
                "REALIZED_JOURNAL_INSTANCE_MISMATCH"
            )

        if not callable(
            portfolio_snapshot_builder
        ):
            raise TypeError(
                "portfolio_snapshot_builder must be callable"
            )

        self.persisting_runtime = (
            persisting_runtime
        )
        self.cash_ledger = cash_ledger
        self.realized_journal = (
            realized_journal
        )
        self.portfolio_snapshot_builder = (
            portfolio_snapshot_builder
        )

        self.last_cash_settlements = (
            MappingProxyType(
                {}
            )
        )

    @property
    def positions(self):
        runtime = getattr(
            self.persisting_runtime,
            "runtime",
            None,
        )

        positions = getattr(
            runtime,
            "positions",
            None,
        )

        if positions is None:
            raise Phase11CashRuntimeError(
                "PHASE11_RUNTIME_POSITIONS_REQUIRED"
            )

        return positions

    def _rebuild_portfolio(
        self,
        *,
        asset_ids,
        result,
    ):
        requested = set(
            asset_ids
        )

        open_positions = {
            str(asset_id): position
            for asset_id, position
            in self.positions.items()
            if str(asset_id)
            in requested
        }

        mtm_records = []

        for asset_id in open_positions:
            item = (
                result
                .accounting_results
                .get(
                    asset_id
                )
            )

            if (
                item is None
                or item.error is not None
                or item.mtm_record is None
            ):
                return (
                    None,
                    (
                        PORTFOLIO_PARTIAL_ACCOUNTING_BLOCKED,
                    ),
                )

            mtm_records.append(
                item.mtm_record
            )

        snapshot = (
            self.portfolio_snapshot_builder(
                cash_pln=(
                    self.cash_ledger
                    .current_cash_pln()
                ),
                mtm_records=tuple(
                    mtm_records
                ),
            )
        )

        return (
            snapshot,
            (),
        )

    def run_cycle(
        self,
        asset_ids,
    ):
        asset_ids = tuple(
            str(asset_id)
            for asset_id in asset_ids
        )

        result = (
            self.persisting_runtime
            .run_cycle(
                asset_ids
            )
        )

        settlements = {}

        for asset_id, persistence in (
            self.persisting_runtime
            .last_persistence
            .items()
        ):
            settlement = (
                self.cash_ledger
                .settle_from_realized_journal(
                    realized_journal=(
                        self.realized_journal
                    ),
                    booking_key=(
                        persistence
                        .record[
                            "booking_key"
                        ]
                    ),
                )
            )

            settlements[
                str(asset_id)
            ] = settlement

        self.last_cash_settlements = (
            MappingProxyType(
                dict(
                    settlements
                )
            )
        )

        (
            portfolio_snapshot,
            portfolio_limits,
        ) = self._rebuild_portfolio(
            asset_ids=asset_ids,
            result=result,
        )

        limitations = [
            limitation
            for limitation
            in tuple(
                result.limitations
            )
            if (
                limitation
                != PORTFOLIO_PARTIAL_ACCOUNTING_BLOCKED
            )
        ]

        limitations.extend(
            portfolio_limits
        )

        return RuntimeAccountingCycleResult(
            execution_cycle=(
                result.execution_cycle
            ),
            accounting_results=(
                result.accounting_results
            ),
            portfolio_snapshot=(
                portfolio_snapshot
            ),
            limitations=tuple(
                dict.fromkeys(
                    limitations
                )
            ),
        )


@dataclass(frozen=True)
class Phase11CashRuntimeBundle:
    runtime: Phase11CashAccountingRuntime
    phase10_bundle: Phase10ProductionRuntimeBundle
    persisting_runtime: PersistingAccountingRuntime
    cash_ledger: Phase11CashLedger
    realized_journal: RealizedAccountingJournal
    startup_reconciliation: tuple


def wire_phase11_cash_runtime(
    *,
    runtime,
    broker,
    runtime_flags,
    policy,
    cash_ledger,
    realized_journal,
    clock=None,
    nbp_provider=None,
    yahoo_provider=None,
    coinbase_provider=None,
    assets=None,
):
    if runtime is None:
        raise TypeError(
            "runtime is required"
        )

    if broker is None:
        raise TypeError(
            "broker is required"
        )

    if not isinstance(
        cash_ledger,
        Phase11CashLedger,
    ):
        raise TypeError(
            "cash_ledger must be Phase11CashLedger"
        )

    if not isinstance(
        realized_journal,
        RealizedAccountingJournal,
    ):
        raise TypeError(
            "realized_journal must be RealizedAccountingJournal"
        )

    startup_reconciliation = (
        reconcile_cash_ledger(
            cash_ledger=cash_ledger,
            realized_journal=(
                realized_journal
            ),
        )
    )

    kwargs = {
        "runtime": runtime,
        "broker": broker,
        "runtime_flags": runtime_flags,
        "policy": policy,
        "clock": clock,
        "nbp_provider": nbp_provider,
        "yahoo_provider": yahoo_provider,
        "coinbase_provider": (
            coinbase_provider
        ),
        "cash_pln_resolver": (
            cash_ledger
            .current_cash_pln
        ),
    }

    if assets is not None:
        kwargs[
            "assets"
        ] = assets

    phase10_bundle = (
        wire_phase10_production_runtime(
            **kwargs
        )
    )

    persisting_runtime = (
        PersistingAccountingRuntime(
            runtime=(
                phase10_bundle
                .wiring
                .runtime
            ),
            journal=(
                realized_journal
            ),
            startup_metadata=(
                phase10_bundle
                .startup_metadata
            ),
        )
    )

    phase11_runtime = (
        Phase11CashAccountingRuntime(
            persisting_runtime=(
                persisting_runtime
            ),
            cash_ledger=(
                cash_ledger
            ),
            realized_journal=(
                realized_journal
            ),
            portfolio_snapshot_builder=(
                phase10_bundle
                .wiring
                .accounting_bridge
                .portfolio_snapshot
            ),
        )
    )

    return Phase11CashRuntimeBundle(
        runtime=phase11_runtime,
        phase10_bundle=(
            phase10_bundle
        ),
        persisting_runtime=(
            persisting_runtime
        ),
        cash_ledger=cash_ledger,
        realized_journal=(
            realized_journal
        ),
        startup_reconciliation=(
            startup_reconciliation
        ),
    )
