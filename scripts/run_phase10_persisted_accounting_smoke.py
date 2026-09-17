from __future__ import annotations

import argparse
from pathlib import Path

from scripts.run_realistic_smoke_fill import (
    build_runtime,
)
from src.accounting.production_startup import (
    Phase10AccountingRuntimePolicy,
    Phase10StartupPolicyError,
    wire_phase10_production_runtime,
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


STARTUP_METADATA_FILENAME = (
    "phase10_startup_metadata.jsonl"
)


def _parser():
    parser = argparse.ArgumentParser(
        description=(
            "Controlled persisted Phase 10 REALISTIC_V2 "
            "accounting entrypoint. PaperBroker only."
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
        "--close-smoke-position",
        action="store_true",
    )

    parser.add_argument(
        "--run-cycle",
        action="store_true",
    )

    parser.add_argument(
        "--confirm-paper-accounting-smoke",
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


def _metadata_path(
    state_dir,
):
    return (
        Path(
            state_dir
        )
        / STARTUP_METADATA_FILENAME
    )


def _persist_and_verify_startup_metadata(
    *,
    state_dir,
    metadata,
    clock,
):
    path = _metadata_path(
        state_dir
    )

    journal = (
        StartupMetadataJournal(
            path,
            clock=clock,
        )
    )

    # Verify all existing records before adding a new startup record.
    before = (
        journal.read_records()
    )

    written = journal.append(
        metadata
    )

    # Verify the complete file again after fsync-backed append.
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

    last = after[-1]

    if (
        last["record_hash"]
        != written["record_hash"]
    ):
        raise StartupMetadataStoreError(
            "STARTUP_METADATA_APPEND_HASH_MISMATCH"
        )

    if (
        last["global_config_hash"]
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
        "PHASE 10 | PERSISTED REALISTIC_V2 "
        "PLN ACCOUNTING STARTUP"
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
        .confirm_paper_accounting_smoke
    ):
        print(
            "EXPLICIT PAPER ACCOUNTING "
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

        bundle = (
            wire_phase10_production_runtime(
                runtime=runtime,
                broker=runtime.broker,
                runtime_flags=(
                    runtime_flags
                ),
                policy=policy,
            )
        )

    except Exception as exc:
        print(
            "PHASE 10 CONSTRUCTION FAILED:",
            f"{type(exc).__name__}: {exc}",
        )
        return 20

    _print_startup_metadata(
        bundle.startup_metadata
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
                    bundle.startup_metadata
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
        "STARTUP METADATA VERIFIED BEFORE PAPER CYCLE"
    )

    try:
        result = (
            bundle.wiring.runtime
            .run_cycle(
                [
                    asset_id,
                ]
            )
        )

    except Exception as exc:
        print(
            "PHASE 10 CYCLE FAILED:",
            f"{type(exc).__name__}: {exc}",
        )
        return 21

    _print_accounting_result(
        result,
        asset_id=asset_id,
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
