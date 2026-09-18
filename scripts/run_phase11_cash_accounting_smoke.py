from __future__ import annotations

import argparse
from pathlib import Path

from scripts.run_realistic_smoke_fill import (
    build_runtime,
)
from src.accounting.cash_ledger import (
    ENTRY_FEE_SETTLED_AT_REALIZATION,
    CashLedgerError,
    Phase11CashLedger,
)
from src.accounting.cash_runtime import (
    wire_phase11_cash_runtime,
)
from src.accounting.production_startup import (
    Phase10AccountingRuntimePolicy,
    Phase10StartupPolicyError,
)
from src.accounting.realized_persistence import (
    RealizedAccountingJournal,
)
from src.accounting.startup_metadata_store import (
    StartupMetadataJournal,
    StartupMetadataStoreError,
)
from src.execution.feature_flags import (
    RealisticV2FeatureFlags,
)
from src.runtime_feature_flags import (
    resolve_phase09_runtime_flags,
)


CASH_LEDGER_FILENAME = (
    "phase11_cash_ledger.jsonl"
)

STARTUP_METADATA_FILENAME = (
    "phase10_startup_metadata.jsonl"
)

REALIZED_ACCOUNTING_FILENAME = (
    "phase10_realized_accounting.jsonl"
)

PRIOR_STATE_EVIDENCE_FILENAMES = (
    "state.json",
    "execution_journal.jsonl",
    STARTUP_METADATA_FILENAME,
    REALIZED_ACCOUNTING_FILENAME,
)


def _parser():
    parser = argparse.ArgumentParser(
        description=(
            "Controlled Phase 11 REALISTIC_V2 "
            "settled-cash PLN accounting entrypoint. "
            "PaperBroker only."
        )
    )

    parser.add_argument(
        "--asset",
        default="BTCUSDT",
    )

    parser.add_argument(
        "--quantity",
        type=float,
        default=0.0001,
    )

    parser.add_argument(
        "--state-dir",
        required=True,
    )

    parser.add_argument(
        "--initial-cash-pln",
        default=None,
    )

    parser.add_argument(
        "--close-smoke-position",
        action="store_true",
    )

    parser.add_argument(
        "--run-cycle",
        action="store_true",
    )

    parser.add_argument(
        "--confirm-phase11-cash-smoke",
        action="store_true",
    )

    parser.add_argument(
        "--realized-market-max-age-seconds",
        type=float,
        required=True,
    )

    parser.add_argument(
        "--realized-daily-reference-max-age-days",
        type=int,
        required=True,
    )

    parser.add_argument(
        "--fx-prefetch-timeout-seconds",
        type=float,
        required=True,
    )

    parser.add_argument(
        "--fx-prefetch-max-workers",
        type=int,
        required=True,
    )

    parser.add_argument(
        "--cycle-timeout-seconds",
        type=float,
        required=True,
    )

    return parser


def _prior_state_evidence(
    state_dir,
):
    state_dir = Path(
        state_dir
    )

    return tuple(
        name
        for name
        in PRIOR_STATE_EVIDENCE_FILENAMES
        if (
            state_dir
            / name
        ).exists()
    )


def _prepare_cash_ledger(
    *,
    state_dir,
    initial_cash_pln,
    clock,
):
    state_dir = Path(
        state_dir
    )

    cash_path = (
        state_dir
        / CASH_LEDGER_FILENAME
    )

    prior_evidence = (
        _prior_state_evidence(
            state_dir
        )
    )

    if (
        not cash_path.exists()
        and prior_evidence
    ):
        raise CashLedgerError(
            "CASH_LEDGER_REQUIRED_FOR_EXISTING_STATE:"
            + ",".join(
                prior_evidence
            )
        )

    ledger = (
        Phase11CashLedger(
            cash_path,
            clock=clock,
        )
    )

    ledger.initialize(
        initial_cash_pln
    )

    records = (
        ledger.read_records()
    )

    return (
        ledger,
        records,
    )


def _persist_and_verify_startup_metadata(
    *,
    state_dir,
    metadata,
    clock,
):
    path = (
        Path(
            state_dir
        )
        / STARTUP_METADATA_FILENAME
    )

    journal = (
        StartupMetadataJournal(
            path,
            clock=clock,
        )
    )

    before = (
        journal.read_records()
    )

    written = journal.append(
        metadata
    )

    after = (
        journal.read_records()
    )

    if (
        len(after)
        != len(before) + 1
    ):
        raise StartupMetadataStoreError(
            "STARTUP_METADATA_APPEND_COUNT_MISMATCH"
        )

    if (
        after[-1][
            "record_hash"
        ]
        != written[
            "record_hash"
        ]
    ):
        raise StartupMetadataStoreError(
            "STARTUP_METADATA_APPEND_HASH_MISMATCH"
        )

    if (
        after[-1][
            "global_config_hash"
        ]
        != metadata.global_config_hash
    ):
        raise StartupMetadataStoreError(
            "STARTUP_METADATA_GLOBAL_HASH_MISMATCH"
        )

    return (
        path,
        written,
        after,
    )


def _print_startup_metadata(
    metadata,
):
    print(
        "Startup schema:",
        metadata.schema,
    )
    print(
        "Execution config hash:",
        metadata.execution_config_hash,
    )
    print(
        "Base global config hash:",
        metadata.base_global_config_hash,
    )
    print(
        "Phase 10 global config hash:",
        metadata.global_config_hash,
    )
    print(
        "Asset registry hash:",
        metadata.asset_registry_hash,
    )
    print(
        "Paper mode:",
        metadata.paper_mode,
    )
    print(
        "Feature flags:",
        dict(
            metadata.feature_flags
        ),
    )
    print(
        "Runtime policy:",
        dict(
            metadata.runtime_policy
        ),
    )
    print(
        "Startup limitations:",
        metadata.limitations,
    )


def _print_accounting_result(
    result,
    *,
    asset_id,
):
    execution_cycle = (
        result.execution_cycle
    )

    asset_result = (
        execution_cycle.results[
            asset_id
        ]
    )

    print(
        "Execution runtime status:",
        asset_result.status.value,
    )

    broker_result = getattr(
        asset_result,
        "broker_result",
        None,
    )

    if (
        broker_result is not None
        and broker_result.execution
        is not None
    ):
        execution = (
            broker_result.execution
        )

        print(
            "Execution ID:",
            execution.execution_id,
        )
        print(
            "Execution price:",
            execution.execution_price,
        )
        print(
            "Execution fee:",
            execution.fee,
        )
        print(
            "Execution config hash:",
            execution.config_hash,
        )

    accounting = (
        result.accounting_results[
            asset_id
        ]
    )

    print(
        "Accounting error:",
        accounting.error,
    )
    print(
        "Accounting limitations:",
        accounting.limitations,
    )
    print(
        "MTM available:",
        accounting.mtm_record
        is not None,
    )
    print(
        "Realized available:",
        accounting.realized_result
        is not None,
    )
    print(
        "Cycle accounting limitations:",
        result.limitations,
    )

    portfolio = (
        result.portfolio_snapshot
    )

    print(
        "Portfolio snapshot available:",
        portfolio is not None,
    )

    if portfolio is not None:
        print(
            "Portfolio cash PLN:",
            portfolio.cash_pln,
        )
        print(
            "Portfolio equity PLN:",
            portfolio.equity_pln,
        )
        print(
            "Portfolio estimated liquidation equity PLN:",
            portfolio.estimated_liquidation_equity_pln,
        )
        print(
            "Portfolio unrealized PnL PLN:",
            portfolio.unrealized_pnl_pln,
        )
        print(
            "Portfolio estimated exit fees PLN:",
            portfolio.estimated_exit_fees_pln,
        )
        print(
            "Portfolio position count:",
            portfolio.position_count,
        )


def main(argv=None):
    args = (
        _parser()
        .parse_args(
            argv
        )
    )

    print()
    print(
        "=" * 92
    )
    print(
        "PHASE 11 | CONTROLLED REALISTIC_V2 "
        "SETTLED CASH PLN ACCOUNTING"
    )
    print(
        "=" * 92
    )
    print(
        "PAPERBROKER ONLY - "
        "NO REAL EXCHANGE ORDERS"
    )
    print()

    asset_id = (
        str(
            args.asset
        )
        .strip()
        .upper()
    )

    if asset_id != "BTCUSDT":
        print(
            "BTCUSDT ONLY"
        )
        return 5

    if args.quantity <= 0:
        print(
            "INVALID QUANTITY"
        )
        return 6

    if (
        args.run_cycle
        and not args
        .confirm_phase11_cash_smoke
    ):
        print(
            "EXPLICIT PHASE 11 CASH "
            "SMOKE CONFIRMATION REQUIRED"
        )
        return 4

    execution_flags = (
        RealisticV2FeatureFlags
        .from_env()
    )

    if not execution_flags.enabled:
        print(
            "REALISTIC_V2 IS DISABLED"
        )
        return 2

    if not execution_flags.execution_enabled:
        print(
            "EXECUTION FEATURE FLAG IS DISABLED"
        )
        return 3

    runtime_flags = (
        resolve_phase09_runtime_flags(
            execution_flags=(
                execution_flags
            ),
        )
    )

    if not runtime_flags.fx.enabled:
        print(
            "FX FEATURE FLAG IS DISABLED"
        )
        return 7

    if (
        not runtime_flags
        .pln_accounting
        .enabled
    ):
        print(
            "PLN ACCOUNTING FEATURE FLAG IS DISABLED"
        )
        return 8

    try:
        policy = (
            Phase10AccountingRuntimePolicy(
                realized_market_max_age_seconds=(
                    args
                    .realized_market_max_age_seconds
                ),
                realized_daily_reference_max_age_days=(
                    args
                    .realized_daily_reference_max_age_days
                ),
                fx_prefetch_timeout_seconds=(
                    args
                    .fx_prefetch_timeout_seconds
                ),
                fx_prefetch_max_workers=(
                    args
                    .fx_prefetch_max_workers
                ),
                cycle_timeout_seconds=(
                    args
                    .cycle_timeout_seconds
                ),
            )
        )

    except (
        Phase10StartupPolicyError,
        TypeError,
        ValueError,
    ) as exc:
        print(
            "INVALID PHASE 10 POLICY:",
            f"{type(exc).__name__}: {exc}",
        )
        return 9

    if policy.limitations:
        print(
            "PHASE 10 POLICY BLOCKED:",
            policy.limitations,
        )
        return 10

    try:
        runtime, store, journal = (
            build_runtime(
                state_dir=(
                    args.state_dir
                ),
                quantity=(
                    args.quantity
                ),
                close_existing=(
                    args
                    .close_smoke_position
                ),
            )
        )

        (
            cash_ledger,
            cash_records_before_wire,
        ) = (
            _prepare_cash_ledger(
                state_dir=(
                    args.state_dir
                ),
                initial_cash_pln=(
                    args.initial_cash_pln
                ),
                clock=runtime.clock,
            )
        )

        realized_journal = (
            RealizedAccountingJournal(
                (
                    Path(
                        args.state_dir
                    )
                    / REALIZED_ACCOUNTING_FILENAME
                ),
                clock=runtime.clock,
            )
        )

        bundle = (
            wire_phase11_cash_runtime(
                runtime=runtime,
                broker=runtime.broker,
                runtime_flags=(
                    runtime_flags
                ),
                policy=policy,
                cash_ledger=(
                    cash_ledger
                ),
                realized_journal=(
                    realized_journal
                ),
            )
        )

    except Exception as exc:
        print(
            "PHASE 11 CONSTRUCTION FAILED:",
            f"{type(exc).__name__}: {exc}",
        )
        print(
            "PAPER EXECUTION CYCLE: NOT RUN"
        )
        print(
            "REAL EXCHANGE ORDERS SENT: 0"
        )
        return 20

    _print_startup_metadata(
        bundle
        .phase10_bundle
        .startup_metadata
    )

    try:
        (
            metadata_path,
            metadata_record,
            metadata_records,
        ) = (
            _persist_and_verify_startup_metadata(
                state_dir=args.state_dir,
                metadata=(
                    bundle
                    .phase10_bundle
                    .startup_metadata
                ),
                clock=runtime.clock,
            )
        )

    except Exception as exc:
        print(
            "STARTUP METADATA PERSISTENCE FAILED:",
            f"{type(exc).__name__}: {exc}",
        )
        print(
            "PAPER EXECUTION CYCLE: NOT RUN"
        )
        print(
            "REAL EXCHANGE ORDERS SENT: 0"
        )
        return 22

    cash_records = (
        cash_ledger.read_records()
    )

    startup_reconciliation = (
        bundle.startup_reconciliation
    )

    print(
        "Startup metadata path:",
        metadata_path,
    )
    print(
        "Startup metadata record hash:",
        metadata_record[
            "record_hash"
        ],
    )
    print(
        "Startup metadata record count:",
        len(
            metadata_records
        ),
    )
    print(
        "STARTUP METADATA PERSISTED: YES"
    )
    print(
        "STARTUP METADATA INTEGRITY: VERIFIED"
    )
    print(
        "Cash ledger path:",
        cash_ledger.path,
    )
    print(
        "Cash ledger record count before wiring:",
        len(
            cash_records_before_wire
        ),
    )
    print(
        "Cash ledger record count after startup reconciliation:",
        len(
            cash_records
        ),
    )
    print(
        "Startup realized reconciliation count:",
        len(
            startup_reconciliation
        ),
    )
    print(
        "Startup realized reconciliation appended:",
        sum(
            1
            for item
            in startup_reconciliation
            if item.appended
        ),
    )
    print(
        "Settled cash PLN:",
        cash_ledger.current_cash_pln(),
    )
    print(
        "Cash limitation:",
        ENTRY_FEE_SETTLED_AT_REALIZATION,
    )
    print(
        "CASH LEDGER INTEGRITY: VERIFIED"
    )

    if not args.run_cycle:
        print(
            "PAPER EXECUTION CYCLE: NOT RUN"
        )
        print(
            "NETWORK ACCOUNTING PREFETCH: NOT RUN"
        )
        print(
            "REAL EXCHANGE ORDERS SENT: 0"
        )
        return 0

    print(
        "STARTUP METADATA AND CASH LEDGER "
        "VERIFIED BEFORE PAPER CYCLE"
    )

    try:
        result = (
            bundle.runtime
            .run_cycle(
                [
                    asset_id,
                ]
            )
        )

    except Exception as exc:
        print(
            "PHASE 11 CYCLE FAILED:",
            f"{type(exc).__name__}: {exc}",
        )
        print(
            "REAL EXCHANGE ORDERS SENT: 0"
        )
        return 21

    _print_accounting_result(
        result,
        asset_id=asset_id,
    )

    persistence = (
        bundle
        .persisting_runtime
        .last_persistence
        .get(
            asset_id
        )
    )

    if persistence is None:
        print(
            "REALIZED ACCOUNTING PERSISTED: NOT_APPLICABLE"
        )
    else:
        print(
            "Realized accounting booking key:",
            persistence.record[
                "booking_key"
            ],
        )
        print(
            "Realized accounting record hash:",
            persistence.record[
                "record_hash"
            ],
        )
        print(
            "Realized accounting append:",
            persistence.appended,
        )
        print(
            "REALIZED ACCOUNTING PERSISTED: YES"
        )

    settlement = (
        bundle
        .runtime
        .last_cash_settlements
        .get(
            asset_id
        )
    )

    if settlement is None:
        print(
            "CASH SETTLEMENT PERSISTED: NOT_APPLICABLE"
        )
    else:
        print(
            "Cash settlement booking key:",
            settlement.record[
                "realized_booking_key"
            ],
        )
        print(
            "Cash settlement exit execution ID:",
            settlement.record[
                "exit_execution_id"
            ],
        )
        print(
            "Cash settlement delta PLN:",
            settlement.record[
                "cash_delta_pln"
            ],
        )
        print(
            "Cash settlement after PLN:",
            settlement.record[
                "cash_after_pln"
            ],
        )
        print(
            "Cash settlement append:",
            settlement.appended,
        )
        print(
            "CASH SETTLEMENT PERSISTED: YES"
        )

    final_cash_records = (
        cash_ledger.read_records()
    )

    print(
        "CASH LEDGER RECORD COUNT:",
        len(
            final_cash_records
        ),
    )
    print(
        "SETTLED CASH PLN:",
        cash_ledger.current_cash_pln(),
    )
    print(
        "CASH LEDGER INTEGRITY: VERIFIED"
    )
    print(
        "Persisted positions:",
        sorted(
            store.load_positions()
        ),
    )
    print(
        "Journal expected open assets:",
        list(
            journal
            .expected_open_assets()
        ),
    )
    print(
        "Journal unresolved:",
        list(
            journal
            .unresolved_client_order_ids()
        ),
    )
    print(
        "STARTUP METADATA PERSISTED: YES"
    )
    print(
        "REAL EXCHANGE ORDERS SENT: 0"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
