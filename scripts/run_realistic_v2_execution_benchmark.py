from __future__ import annotations

from datetime import datetime, timezone
from types import (
    MappingProxyType,
    SimpleNamespace,
)

from src.accounting.feature_flags import (
    PlnAccountingFeatureFlags,
)
from src.config_fingerprint import (
    asset_registry_hash,
    build_phase09_feature_flags,
    global_config_hash,
)
from src.core.clock import FixedClock
from src.execution.feature_flags import (
    RealisticV2FeatureFlags,
)
from src.fx.feature_flags import FxFeatureFlags
from src.data.assets import get_asset
from src.data.market_data import (
    DataQuality,
    ExecutionQuality,
    MarketSnapshot,
    ProviderStatus,
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
from src.market.market_session import (
    MarketSessionSnapshot,
    SessionQuality,
    SessionState,
)


NOW = datetime(
    2026,
    9,
    16,
    15,
    0,
    tzinfo=timezone.utc,
)


def _snapshot(
    *,
    bid,
    ask,
    last,
):
    return MarketSnapshot(
        asset_id="BTCUSDT",
        bid=float(bid),
        ask=float(ask),
        last=float(last),
        provider_timestamp=NOW,
        received_at=NOW,
        data_quality=DataQuality.REALTIME,
        delayed=False,
        quote_age_seconds=0.0,
        provider_status=(
            ProviderStatus.CONNECTED
        ),
        execution_quality=(
            ExecutionQuality.REAL_BOOK
        ),
    )


class FixtureMarketData:
    def __init__(self):
        self._snapshots = [
            _snapshot(
                bid=9999.0,
                ask=10001.0,
                last=10000.0,
            ),
            _snapshot(
                bid=10049.0,
                ask=10051.0,
                last=10050.0,
            ),
        ]

    def run_cycle(
        self,
        asset_ids,
    ):
        if tuple(asset_ids) != (
            "BTCUSDT",
        ):
            raise ValueError(
                "Benchmark supports BTCUSDT only"
            )

        if not self._snapshots:
            raise RuntimeError(
                "Benchmark fixture exhausted"
            )

        snapshot = (
            self._snapshots.pop(0)
        )

        return SimpleNamespace(
            snapshots=MappingProxyType(
                {
                    "BTCUSDT": snapshot,
                }
            ),
            errors=MappingProxyType(
                {}
            ),
            duration_seconds=0.0,
            timed_out=False,
        )


class FixtureSessionService:
    def get_session(
        self,
        asset_id,
        at,
    ):
        return MarketSessionSnapshot(
            asset_id=asset_id,
            session_id="FIXTURE",
            state=SessionState.OPEN,
            session_quality=(
                SessionQuality.EXCHANGE_CALENDAR
            ),
            observed_at=NOW,
            timezone_name="UTC",
            local_time=NOW,
            reason=(
                "DETERMINISTIC_EXECUTION_FIXTURE"
            ),
            calendar_version="fixture-v1",
        )


class FixtureDecisionProvider:
    def __init__(self):
        self._index = 0

    def __call__(
        self,
        *,
        asset_id,
        snapshot,
        position,
    ):
        if self._index == 0:
            self._index += 1

            return ExecutionDecision(
                side=OrderSide.BUY,
                intent=OrderIntent.ENTRY,
                quantity=0.01,
                stop_loss=9500.0,
                take_profit=11000.0,
                signal_reference=(
                    "FIXTURE_ENTRY"
                ),
            )

        if self._index == 1:
            self._index += 1

            if position is None:
                raise RuntimeError(
                    "Fixture position missing"
                )

            return ExecutionDecision(
                side=OrderSide.SELL,
                intent=OrderIntent.EXIT,
                quantity=(
                    position.quantity
                ),
                exit_reason=(
                    "FIXTURE_EXIT"
                ),
                signal_reference=(
                    "FIXTURE_EXIT"
                ),
            )

        return None


def run_benchmark():
    broker = PaperBroker(
        clock=FixedClock(NOW),
        asset_resolver=get_asset,
        slippage_model=(
            FixedBpsSlippage(
                1.0
            )
        ),
        trading_fee_rate=0.0004,
    )

    execution_flags = RealisticV2FeatureFlags(
        enabled=True,
        execution_enabled=True,
        paper_mode=PaperMode.REALISTIC_PAPER,
    )
    fx_flags = FxFeatureFlags(enabled=False)
    pln_flags = PlnAccountingFeatureFlags(
        enabled=False
    )

    phase09_flags = build_phase09_feature_flags(
        realistic_v2_enabled=(
            execution_flags.enabled
        ),
        realistic_v2_execution_enabled=(
            execution_flags.execution_enabled
        ),
        fx_enabled=fx_flags.enabled,
        pln_accounting_enabled=(
            pln_flags.enabled
        ),
    )

    execution_config_hash = (
        broker.config_hash_for(
            execution_flags.paper_mode
        )
    )

    benchmark_global_config_hash = (
        global_config_hash(
            execution_config_hash=(
                execution_config_hash
            ),
            paper_mode=(
                execution_flags.paper_mode
            ),
            feature_flags=phase09_flags,
        )
    )

    runtime = RealisticPaperRuntime(
        market_data_service=(
            FixtureMarketData()
        ),
        market_session_service=(
            FixtureSessionService()
        ),
        broker=broker,
        decision_provider=(
            FixtureDecisionProvider()
        ),
        clock=FixedClock(NOW),
        paper_mode=(
            PaperMode.REALISTIC_PAPER
        ),
    )

    entry_cycle = runtime.run_cycle(
        ["BTCUSDT"]
    )

    entry_result = (
        entry_cycle.results[
            "BTCUSDT"
        ]
    )

    entry_execution = (
        entry_result
        .broker_result
        .execution
    )

    if entry_execution is None:
        raise RuntimeError(
            "Benchmark entry did not execute"
        )

    exit_cycle = runtime.run_cycle(
        ["BTCUSDT"]
    )

    exit_result = (
        exit_cycle.results[
            "BTCUSDT"
        ]
    )

    exit_execution = (
        exit_result
        .broker_result
        .execution
    )

    if exit_execution is None:
        raise RuntimeError(
            "Benchmark exit did not execute"
        )

    return {
        "label": (
            "DETERMINISTIC_EXECUTION_FIXTURE_"
            "NOT_MARKET_PERFORMANCE"
        ),
        "benchmark_metadata": {
            "metadata_schema": "phase09-a11-v1",
            "execution_profile": "REALISTIC_V2",
            "paper_mode": (
                execution_flags.paper_mode.value
            ),
            "feature_flags": phase09_flags,
            "asset_registry_hash": (
                asset_registry_hash()
            ),
            "execution_config_hash": (
                execution_config_hash
            ),
            "global_config_hash": (
                benchmark_global_config_hash
            ),
        },
        "entry_reference_price": (
            entry_execution.reference_price
        ),
        "entry_execution_price": (
            entry_execution.execution_price
        ),
        "entry_spread": (
            entry_execution.spread
        ),
        "entry_slippage": (
            entry_execution.slippage
        ),
        "entry_fee": (
            entry_execution.fee
        ),
        "exit_reference_price": (
            exit_execution.reference_price
        ),
        "exit_execution_price": (
            exit_execution.execution_price
        ),
        "exit_spread": (
            exit_execution.spread
        ),
        "exit_slippage": (
            exit_execution.slippage
        ),
        "exit_fee": (
            exit_execution.fee
        ),
        "entry_config_hash": (
            entry_execution.config_hash
        ),
        "exit_config_hash": (
            exit_execution.config_hash
        ),
        "config_hash_match": (
            entry_execution.config_hash
            == exit_execution.config_hash
        ),
        "positions_after_round_trip": (
            tuple(
                sorted(
                    runtime.positions
                )
            )
        ),
    }


def main():
    result = run_benchmark()

    print("=" * 88)
    print(
        "REALISTIC_V2 DETERMINISTIC EXECUTION BENCHMARK"
    )
    print("=" * 88)

    print(
        "LABEL:",
        result["label"],
    )

    print(
        "PROFILE: REALISTIC_V2"
    )

    print(
        "PAPER_MODE: realistic_paper"
    )

    print(
        "EXECUTION_QUALITY: REAL_BOOK FIXTURE"
    )

    print(
        "SLIPPAGE_MODEL: FixedBpsSlippage(1.0)"
    )

    print(
        "FEE_RATE: 0.0004"
    )

    print(
        "EXECUTION_CONFIG_HASH:",
        result["benchmark_metadata"][
            "execution_config_hash"
        ],
    )
    print(
        "GLOBAL_CONFIG_HASH:",
        result["benchmark_metadata"][
            "global_config_hash"
        ],
    )
    print(
        "ASSET_REGISTRY_HASH:",
        result["benchmark_metadata"][
            "asset_registry_hash"
        ],
    )
    print(
        "FEATURE_FLAGS:",
        result["benchmark_metadata"][
            "feature_flags"
        ],
    )

    print()

    for key in (
        "entry_reference_price",
        "entry_execution_price",
        "entry_spread",
        "entry_slippage",
        "entry_fee",
        "exit_reference_price",
        "exit_execution_price",
        "exit_spread",
        "exit_slippage",
        "exit_fee",
        "entry_config_hash",
        "exit_config_hash",
        "config_hash_match",
        "positions_after_round_trip",
    ):
        print(
            f"{key}: {result[key]}"
        )

    print()
    print(
        "MARKET PERFORMANCE CLAIM: NONE"
    )

    print(
        "PLN ACCOUNTING CLAIM: NONE"
    )

    print(
        "BENCHMARK RESULT: PASS"
    )


if __name__ == "__main__":
    main()
