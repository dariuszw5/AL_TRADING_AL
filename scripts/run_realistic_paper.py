from __future__ import annotations

import argparse

from src.data.assets import get_asset
from src.execution.feature_flags import (
    RealisticV2FeatureFlags,
)
from src.execution.live_preflight import (
    build_live_preflight,
)


def _parser():
    parser = argparse.ArgumentParser(
        description=(
            "REALISTIC_V2 live-data preflight. "
            "No real or paper orders are submitted."
        )
    )

    parser.add_argument(
        "--asset",
        action="append",
        dest="assets",
        help=(
            "Canonical asset_id. Repeat for "
            "multiple assets. Default: BTCUSDT."
        ),
    )

    parser.add_argument(
        "--execute",
        action="store_true",
        help=(
            "Reserved for a later stateful "
            "REALISTIC_V2 paper runner."
        ),
    )

    return parser


def _validate_assets(
    asset_ids,
):
    result = []

    for asset_id in asset_ids:
        canonical = str(
            asset_id
        ).strip().upper()

        try:
            asset = get_asset(
                canonical
            )
        except Exception:
            return (
                None,
                canonical,
            )

        result.append(
            asset.asset_id
        )

    return (
        tuple(
            dict.fromkeys(
                result
            )
        ),
        None,
    )


def main(argv=None):
    args = _parser().parse_args(
        argv
    )

    flags = (
        RealisticV2FeatureFlags
        .from_env()
    )

    print()
    print("=" * 92)
    print(
        "AL TRADING AGENT | "
        "REALISTIC_V2 LIVE PREFLIGHT"
    )
    print("=" * 92)
    print(
        "PRE-FLIGHT ONLY - "
        "NO PAPER ORDERS - "
        "NO REAL ORDERS"
    )
    print()

    if not flags.enabled:
        print(
            "REALISTIC_V2 IS DISABLED"
        )
        print(
            "Set "
            "AL_TRADING_REALISTIC_V2_ENABLED=1 "
            "to permit the live-data preflight."
        )

        return 2

    if args.execute:
        print(
            "PAPER EXECUTION BLOCKED"
        )
        print(
            "Phase 08 B.5 has no persistent "
            "REALISTIC_V2 position/account state."
        )
        print(
            "Refusing to create a paper position "
            "that could be forgotten after restart."
        )

        return 3

    asset_ids = (
        args.assets
        or [
            "BTCUSDT",
        ]
    )

    asset_ids, unknown = (
        _validate_assets(
            asset_ids
        )
    )

    if unknown is not None:
        print(
            f"UNKNOWN ASSET: {unknown}"
        )

        return 4

    print(
        "Paper mode:",
        flags.paper_mode.value,
    )

    print(
        "Assets:",
        ", ".join(
            asset_ids
        ),
    )

    print()

    preflight = build_live_preflight(
        paper_mode=(
            flags.paper_mode
        )
    )

    cycle = preflight.run(
        asset_ids
    )

    for asset_id in asset_ids:
        result = (
            cycle.results[
                asset_id
            ]
        )

        print(
            f"{asset_id:<15} "
            f"status={result.status.value:<13} "
            f"allowed={str(result.allowed):<5} "
            f"data={str(result.data_quality):<10} "
            f"execution={str(result.execution_quality):<18} "
            f"session={str(result.session_state):<13} "
            f"session_q={str(result.session_quality):<18} "
            f"provider={str(result.provider_status):<12}"
        )

        if (
            result.rejection_reason
            is not None
        ):
            print(
                "  rejection:",
                result.rejection_reason,
            )

        if result.error is not None:
            print(
                "  error:",
                result.error,
            )

        if result.labels:
            print(
                "  labels:",
                ", ".join(
                    result.labels
                ),
            )

        if (
            result.quote_age_seconds
            is not None
        ):
            print(
                "  quote_age_seconds:",
                result.quote_age_seconds,
            )

    print()
    print(
        "cycle_duration_seconds:",
        cycle.duration_seconds,
    )

    print(
        "cycle_timed_out:",
        cycle.timed_out,
    )

    print()
    print(
        "RESULT: LIVE DATA CHECKED, "
        "NO ORDERS SUBMITTED"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
