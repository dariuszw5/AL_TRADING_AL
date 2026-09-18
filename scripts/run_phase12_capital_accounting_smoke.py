from __future__ import annotations

import argparse
from pathlib import Path

from scripts.run_phase11_cash_accounting_smoke import (
    CASH_LEDGER_FILENAME,
    REALIZED_ACCOUNTING_FILENAME,
    STARTUP_METADATA_FILENAME,
    _persist_and_verify_startup_metadata,
    _prepare_cash_ledger,
    _print_accounting_result,
    _print_startup_metadata,
)
from scripts.run_realistic_smoke_fill import (
    build_runtime,
)
from src.accounting.cash_ledger import (
    ENTRY_FEE_SETTLED_AT_REALIZATION,
)
from src.accounting.production_startup import (
    Phase10AccountingRuntimePolicy,
    Phase10StartupPolicyError,
)
from src.accounting.realized_persistence import (
    RealizedAccountingJournal,
)
from src.execution.capital_feature_flags import (
    CapitalAdmissionFeatureFlags,
)
from src.execution.capital_runtime import (
    wire_phase12_capital_runtime,
)
from src.execution.capital_startup import (
    Phase12CapitalAdmissionPolicy,
    Phase12StartupPolicyError,
)
from src.execution.capital_startup_store import (
    Phase12StartupMetadataJournal,
    Phase12StartupMetadataStoreError,
)
from src.execution.feature_flags import (
    RealisticV2FeatureFlags,
)
from src.data.assets import (
    get_asset,
)
from src.runtime_feature_flags import (
    resolve_phase09_runtime_flags,
)


PHASE12_STARTUP_METADATA_FILENAME = (
    "phase12_startup_metadata.jsonl"
)


def _parser():
    parser = argparse.ArgumentParser(
        description=(
            "Controlled Phase 12 REALISTIC_V2 "
            "cash-backed capital-admission entrypoint. "
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
        "--confirm-phase12-capital-smoke",
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


def _persist_and_verify_phase12_startup_metadata(
    *,
    state_dir,
    metadata,
    clock,
):
    path = (
        Path(
            state_dir
        )
        / PHASE12_STARTUP_METADATA_FILENAME
    )

    journal = (
        Phase12StartupMetadataJournal(
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
        raise Phase12StartupMetadataStoreError(
            "PHASE12_STARTUP_APPEND_COUNT_MISMATCH"
        )

    if (
        after[-1][
            "record_hash"
        ]
        != written[
            "record_hash"
        ]
    ):
        raise Phase12StartupMetadataStoreError(
            "PHASE12_STARTUP_APPEND_HASH_MISMATCH"
        )

    if (
        after[-1][
            "global_config_hash"
        ]
        != metadata.global_config_hash
    ):
        raise Phase12StartupMetadataStoreError(
            "PHASE12_STARTUP_GLOBAL_HASH_MISMATCH"
        )

    if (
        after[-1][
            "phase10_global_config_hash"
        ]
        != metadata.phase10_global_config_hash
    ):
        raise Phase12StartupMetadataStoreError(
            "PHASE12_STARTUP_PHASE10_HASH_MISMATCH"
        )

    return (
        path,
        written,
        after,
    )


def _print_phase12_startup_metadata(
    metadata,
):
    print(
        "Phase 12 startup schema:",
        metadata.schema,
    )
    print(
        "Phase 12 execution config hash:",
        metadata.execution_config_hash,
    )
    print(
        "Phase 10 global config hash:",
        metadata.phase10_global_config_hash,
    )
    print(
        "Phase 12 global config hash:",
        metadata.global_config_hash,
    )
    print(
        "Phase 12 asset registry hash:",
        metadata.asset_registry_hash,
    )
    print(
        "Phase 12 paper mode:",
        metadata.paper_mode,
    )
    print(
        "Phase 12 feature flags:",
        dict(
            metadata.phase12_feature_flags
        ),
    )
    print(
        "Phase 12 capital policy:",
        dict(
            metadata.capital_policy
        ),
    )


def _print_capital_admission(
    result,
    *,
    asset_id,
):
    asset_result = (
        result
        .execution_cycle
        .results[
            asset_id
        ]
    )

    capital = getattr(
        asset_result,
        "capital_admission",
        None,
    )

    if capital is None:
        print(
            "Capital admission:",
            "NOT_APPLICABLE",
        )
        return

    print(
        "Capital admission allowed:",
        capital.allowed,
    )
    print(
        "Capital admission reason:",
        capital.reason,
    )
    print(
        "Capital admission error:",
        capital.error,
    )

    exposure = (
        capital.exposure_result
    )

    if exposure is not None:
        print(
            "Capital proposed exposure available:",
            exposure.available,
        )
        print(
            "Capital proposed exposure PLN:",
            exposure.exposure_pln,
        )
        print(
            "Capital FX path:",
            exposure.fx_path,
        )
        print(
            "Capital FX freshness:",
            (
                None
                if exposure.fx_freshness
                is None
                else exposure.fx_freshness.value
            ),
        )

    admission = (
        capital.admission_decision
    )

    if admission is not None:
        print(
            "Capital settled cash PLN:",
            admission.settled_cash_pln,
        )
        print(
            "Capital limit PLN:",
            admission.capital_limit_pln,
        )
        print(
            "Capital headroom PLN:",
            admission.headroom_pln,
        )


def main(
    argv=None,
):
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
        "PHASE 12 | CONTROLLED REALISTIC_V2 "
        "CASH-BACKED CAPITAL ADMISSION"
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
        .confirm_phase12_capital_smoke
    ):
        print(
            "EXPLICIT PHASE 12 CAPITAL "
            "SMOKE CONFIRMATION REQUIRED"
        )
        return 4

    try:
        execution_flags = (
            RealisticV2FeatureFlags
            .from_env()
        )

        capital_flags = (
            CapitalAdmissionFeatureFlags
            .from_env()
        )

    except ValueError as exc:
        print(
            "INVALID FEATURE FLAG:",
            f"{type(exc).__name__}: {exc}",
        )
        return 11

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

    if not capital_flags.enabled:
        print(
            "CAPITAL ADMISSION FEATURE FLAG IS DISABLED"
        )
        return 12

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
        phase10_policy = (
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

        capital_policy = (
            Phase12CapitalAdmissionPolicy
            .from_asset(
                get_asset(
                    asset_id
                )
            )
        )

    except (
        Phase10StartupPolicyError,
        Phase12StartupPolicyError,
        TypeError,
        ValueError,
    ) as exc:
        print(
            "INVALID STARTUP POLICY:",
            f"{type(exc).__name__}: {exc}",
        )
        return 9

    if phase10_policy.limitations:
        print(
            "PHASE 10 POLICY BLOCKED:",
            phase10_policy.limitations,
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
            wire_phase12_capital_runtime(
                runtime=runtime,
                broker=runtime.broker,
                runtime_flags=(
                    runtime_flags
                ),
                phase10_policy=(
                    phase10_policy
                ),
                cash_ledger=(
                    cash_ledger
                ),
                realized_journal=(
                    realized_journal
                ),
                capital_flags=(
                    capital_flags
                ),
                capital_policy=(
                    capital_policy
                ),
            )
        )

    except Exception as exc:
        print(
            "PHASE 12 CONSTRUCTION FAILED:",
            f"{type(exc).__name__}: {exc}",
        )
        print(
            "PAPER EXECUTION CYCLE: NOT RUN"
        )
        print(
            "REAL EXCHANGE ORDERS SENT: 0"
        )
        return 20

    phase10_metadata = (
        bundle
        .phase11_bundle
        .phase10_bundle
        .startup_metadata
    )

    _print_startup_metadata(
        phase10_metadata
    )

    _print_phase12_startup_metadata(
        bundle.phase12_metadata
    )

    try:
        (
            phase10_metadata_path,
            phase10_metadata_record,
            phase10_metadata_records,
        ) = (
            _persist_and_verify_startup_metadata(
                state_dir=args.state_dir,
                metadata=(
                    phase10_metadata
                ),
                clock=runtime.clock,
            )
        )

        (
            phase12_metadata_path,
            phase12_metadata_record,
            phase12_metadata_records,
        ) = (
            _persist_and_verify_phase12_startup_metadata(
                state_dir=args.state_dir,
                metadata=(
                    bundle
                    .phase12_metadata
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
        bundle
        .phase11_bundle
        .startup_reconciliation
    )

    print(
        "Phase 10 startup metadata path:",
        phase10_metadata_path,
    )
    print(
        "Phase 10 startup metadata record hash:",
        phase10_metadata_record[
            "record_hash"
        ],
    )
    print(
        "Phase 10 startup metadata record count:",
        len(
            phase10_metadata_records
        ),
    )
    print(
        "PHASE 10 STARTUP METADATA PERSISTED: YES"
    )
    print(
        "PHASE 10 STARTUP METADATA INTEGRITY: VERIFIED"
    )

    print(
        "Phase 12 startup metadata path:",
        phase12_metadata_path,
    )
    print(
        "Phase 12 startup metadata record hash:",
        phase12_metadata_record[
            "record_hash"
        ],
    )
    print(
        "Phase 12 startup metadata record count:",
        len(
            phase12_metadata_records
        ),
    )
    print(
        "PHASE 12 STARTUP METADATA PERSISTED: YES"
    )
    print(
        "PHASE 12 STARTUP METADATA INTEGRITY: VERIFIED"
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
        "PHASE 10 + PHASE 12 STARTUP METADATA "
        "AND CASH LEDGER VERIFIED BEFORE PAPER CYCLE"
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
            "PHASE 12 CYCLE FAILED:",
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

    _print_capital_admission(
        result,
        asset_id=asset_id,
    )

    persistence = (
        bundle
        .phase11_bundle
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
        "PHASE 10 STARTUP METADATA PERSISTED: YES"
    )
    print(
        "PHASE 12 STARTUP METADATA PERSISTED: YES"
    )
    print(
        "REAL EXCHANGE ORDERS SENT: 0"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
