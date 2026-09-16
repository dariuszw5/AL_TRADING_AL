from __future__ import annotations

import argparse
from pathlib import Path

from src.core.clock import SystemClock
from src.data.assets import get_asset
from src.data.data_provider import DataProvider
from src.data.parallel_market_data_service import (
    ParallelMarketDataService,
)
from src.execution.execution_journal import (
    RealisticExecutionJournal,
)
from src.execution.feature_flags import (
    RealisticV2FeatureFlags,
)
from src.execution.models import (
    OrderIntent,
    OrderSide,
    PaperMode,
)
from src.execution.paper_broker import (
    PaperBroker,
)
from src.execution.runtime import (
    ExecutionDecision,
    RealisticPaperRuntime,
)
from src.execution.slippage import (
    FixedBpsSlippage,
)
from src.execution.state_store import (
    RealisticPaperStateStore,
)
from src.market.market_session import (
    MarketSessionService,
)


DEFAULT_STATE_DIR = Path(
    "data"
) / "realistic_v2_state" / "smoke_btcusdt"


class SmokeEntryDecision:
    """
    Technical paper-execution smoke test.

    This is deliberately NOT a strategy signal.
    """

    def __init__(
        self,
        *,
        quantity,
    ):
        self.quantity = float(
            quantity
        )

    def __call__(
        self,
        *,
        asset_id,
        snapshot,
        position,
    ):
        if position is not None:
            return None

        reference = (
            snapshot.ask
            or snapshot.last
        )

        if reference is None:
            return None

        stop_loss = (
            float(reference)
            * 0.95
        )

        risk_distance = (
            float(reference)
            - stop_loss
        )

        take_profit = (
            float(reference)
            + (
                2.0
                * risk_distance
            )
        )

        return ExecutionDecision(
            side=OrderSide.BUY,
            intent=OrderIntent.ENTRY,
            quantity=self.quantity,
            stop_loss=stop_loss,
            take_profit=take_profit,
            signal_reference=(
                "CONTROLLED_SMOKE_ENTRY_"
                "NOT_STRATEGY_SIGNAL"
            ),
        )


def build_runtime(
    *,
    state_dir,
    quantity,
):
    clock = SystemClock()

    state_dir = Path(
        state_dir
    )

    provider = DataProvider(
        clock=clock,
        request_timeout_seconds=8.0,
    )

    market_data = (
        ParallelMarketDataService(
            provider,
            clock=clock,
            cycle_timeout_seconds=20.0,
            stale_after_seconds=120.0,
            per_asset_timeout_seconds=8.0,
            max_workers=1,
        )
    )

    journal = (
        RealisticExecutionJournal(
            state_dir
            / "execution_journal.jsonl",
            clock=clock,
        )
    )

    broker = PaperBroker(
        clock=clock,
        asset_resolver=get_asset,
        slippage_model=(
            FixedBpsSlippage(
                1.0
            )
        ),
        trading_fee_rate=0.0004,
        execution_journal=journal,
    )

    store = (
        RealisticPaperStateStore(
            state_dir
            / "state.json",
            clock=clock,
        )
    )

    runtime = RealisticPaperRuntime(
        market_data_service=(
            market_data
        ),
        market_session_service=(
            MarketSessionService()
        ),
        broker=broker,
        decision_provider=(
            SmokeEntryDecision(
                quantity=quantity
            )
        ),
        clock=clock,
        paper_mode=(
            PaperMode.REALISTIC_PAPER
        ),
        state_store=store,
    )

    return (
        runtime,
        store,
        journal,
    )


def _parser():
    parser = argparse.ArgumentParser(
        description=(
            "Controlled REALISTIC_V2 paper "
            "execution smoke test. "
            "Never sends a real exchange order."
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
        "--confirm-paper-smoke",
        action="store_true",
    )

    parser.add_argument(
        "--verify-only",
        action="store_true",
    )

    return parser


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
        "REALISTIC_V2 CONTROLLED "
        "PAPER SMOKE | BTCUSDT"
    )
    print("=" * 92)

    print(
        "PAPER BROKER ONLY - "
        "NO REAL EXCHANGE ORDER"
    )

    print(
        "NOT A STRATEGY SIGNAL"
    )

    print()

    if (
        str(args.asset).upper()
        != "BTCUSDT"
    ):
        print(
            "BTCUSDT ONLY"
        )
        return 5

    if args.quantity <= 0:
        print(
            "INVALID QUANTITY"
        )
        return 6

    if args.verify_only:
        try:
            runtime, store, journal = (
                build_runtime(
                    state_dir=(
                        args.state_dir
                    ),
                    quantity=(
                        args.quantity
                    ),
                )
            )

        except Exception as exc:
            print(
                "RECOVERY CHECK FAILED:",
                f"{type(exc).__name__}: {exc}",
            )

            return 20

        positions = (
            store.load_positions()
        )

        print(
            "Recovery check: OK"
        )

        print(
            "Open positions:",
            sorted(
                positions
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

        return 0

    if not flags.enabled:
        print(
            "REALISTIC_V2 IS DISABLED"
        )
        return 2

    if not flags.execution_enabled:
        print(
            "EXECUTION FEATURE FLAG IS DISABLED"
        )
        return 3

    if not args.confirm_paper_smoke:
        print(
            "EXPLICIT CONFIRMATION REQUIRED"
        )
        return 4

    runtime, store, journal = (
        build_runtime(
            state_dir=args.state_dir,
            quantity=args.quantity,
        )
    )

    result = runtime.run_cycle(
        ["BTCUSDT"]
    )

    asset_result = (
        result.results[
            "BTCUSDT"
        ]
    )

    print(
        "Runtime status:",
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
            "Reference price:",
            execution.reference_price,
        )

        print(
            "Execution price:",
            execution.execution_price,
        )

        print(
            "Spread:",
            execution.spread,
        )

        print(
            "Slippage:",
            execution.slippage,
        )

        print(
            "Fee:",
            execution.fee,
        )

        print(
            "Config hash:",
            execution.config_hash,
        )

    positions = (
        store.load_positions()
    )

    print(
        "Persisted positions:",
        sorted(
            positions
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

    print()
    print(
        "REAL EXCHANGE ORDERS SENT: 0"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
