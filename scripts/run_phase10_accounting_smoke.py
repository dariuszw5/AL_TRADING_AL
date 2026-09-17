from __future__ import annotations

import argparse

from scripts.run_realistic_smoke_fill import (
    DEFAULT_STATE_DIR,
    build_runtime,
)
from src.accounting.production_startup import (
    Phase10AccountingRuntimePolicy,
    Phase10StartupPolicyError,
    wire_phase10_production_runtime,
)
from src.execution.feature_flags import (
    RealisticV2FeatureFlags,
)
from src.runtime_feature_flags import (
    resolve_phase09_runtime_flags,
)


def _parser():
    parser = argparse.ArgumentParser(
        description=(
            "Controlled REALISTIC_V2 accounting "
            "construction/smoke entrypoint. "
            "PaperBroker only; never sends a real exchange order."
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
        default=str(
            DEFAULT_STATE_DIR
        ),
    )

    parser.add_argument(
        "--close-smoke-position",
        action="store_true",
        help=(
            "Use the existing controlled smoke decision "
            "to close an already-open BTCUSDT smoke position."
        ),
    )

    parser.add_argument(
        "--run-cycle",
        action="store_true",
        help=(
            "Run one controlled PaperBroker cycle. "
            "Without this flag the command only verifies construction."
        ),
    )

    parser.add_argument(
        "--confirm-paper-accounting-smoke",
        action="store_true",
        help=(
            "Required together with --run-cycle. "
            "Confirms paper-only stateful execution."
        ),
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
        "PHASE 10 | CONTROLLED REALISTIC_V2 "
        "PLN ACCOUNTING SMOKE"
    )
    print(
        "=" * 92
    )

    print(
        "PAPERBROKER ONLY - "
        "NO REAL EXCHANGE ORDERS"
    )

    print(
        "DEFAULT MODE: CONSTRUCTION VERIFY ONLY"
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

    print()

    if not args.run_cycle:
        print(
            "RESULT: PHASE 10 ACCOUNTING "
            "RUNTIME CONSTRUCTION VERIFIED"
        )

        print(
            "NETWORK ACCOUNTING PREFETCH: NOT RUN"
        )

        print(
            "PAPER EXECUTION CYCLE: NOT RUN"
        )

        print(
            "STARTUP METADATA PERSISTED: NO"
        )

        print(
            "REAL EXCHANGE ORDERS SENT: 0"
        )

        return 0

    print(
        "Smoke action:",
        (
            "CLOSE_EXISTING_POSITION"
            if args.close_smoke_position
            else "OPEN_POSITION"
        ),
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
        "FX provider errors:",
        dict(
            bundle
            .wiring
            .fx_resolver
            .provider_errors
        ),
    )

    print(
        "FX contract errors:",
        dict(
            bundle
            .wiring
            .fx_resolver
            .contract_errors
        ),
    )

    print(
        "FX prefetch duration seconds:",
        bundle
        .wiring
        .fx_resolver
        .last_prefetch_duration_seconds,
    )

    print(
        "FX prefetch timed out:",
        bundle
        .wiring
        .fx_resolver
        .last_prefetch_timed_out,
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
        "STARTUP METADATA PERSISTED: NO"
    )

    print(
        "REAL EXCHANGE ORDERS SENT: 0"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
