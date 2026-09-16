from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Mapping

from src.core.clock import Clock, SystemClock
from src.data.data_provider import DataProvider
from src.data.parallel_market_data_service import (
    ParallelMarketDataService,
)
from src.market.market_session import (
    MarketSessionService,
)

from .execution_policy import (
    ExecutionPolicy,
    enum_value,
)
from .models import (
    ExecutionProfile,
    Order,
    OrderIntent,
    OrderSide,
    PaperMode,
)


class PreflightAssetStatus(
    str,
    Enum,
):
    READY = "READY"
    BLOCKED = "BLOCKED"
    DATA_ERROR = "DATA_ERROR"
    SESSION_ERROR = "SESSION_ERROR"


@dataclass(frozen=True)
class PreflightAssetResult:
    asset_id: str
    status: PreflightAssetStatus

    allowed: bool

    rejection_reason: str | None = None
    error: str | None = None

    data_quality: str | None = None
    execution_quality: str | None = None
    provider_status: str | None = None

    session_state: str | None = None
    session_quality: str | None = None

    quote_age_seconds: float | None = None

    labels: tuple[str, ...] = ()


@dataclass(frozen=True)
class PreflightCycleResult:
    results: Mapping[
        str,
        PreflightAssetResult,
    ]

    market_data_errors: Mapping[
        str,
        str,
    ]

    duration_seconds: float
    timed_out: bool


class RealisticLivePreflight:
    """
    Live REALISTIC_V2 readiness probe.

    It fetches real provider data and evaluates
    execution/session policy.

    It never submits an order and never mutates
    paper position/account state.
    """

    def __init__(
        self,
        *,
        market_data_service,
        market_session_service,
        clock: Clock | None = None,
        paper_mode: PaperMode = (
            PaperMode.REALISTIC_PAPER
        ),
        policy=None,
    ):
        self.market_data_service = (
            market_data_service
        )

        self.market_session_service = (
            market_session_service
        )

        self.clock = (
            clock
            or SystemClock()
        )

        self.paper_mode = paper_mode

        self.policy = (
            policy
            or ExecutionPolicy()
        )

    def _probe_order(
        self,
        asset_id,
    ):
        return Order(
            order_id=(
                f"preflight-{asset_id}"
            ),
            client_order_id=(
                f"preflight-{asset_id}"
            ),
            asset_id=asset_id,
            side=OrderSide.BUY,
            quantity=1.0,
            intent=OrderIntent.ENTRY,
            created_at=self.clock.now(),
            execution_profile=(
                ExecutionProfile.REALISTIC_V2
            ),
            paper_mode=self.paper_mode,
            signal_reference=(
                "LIVE_PREFLIGHT"
            ),
        )

    def run(
        self,
        asset_ids,
    ):
        asset_ids = tuple(
            asset_ids
        )

        market_cycle = (
            self.market_data_service
            .run_cycle(
                asset_ids
            )
        )

        results = {}

        for asset_id in asset_ids:
            market_snapshot = (
                market_cycle.snapshots.get(
                    asset_id
                )
            )

            if market_snapshot is None:
                error = (
                    market_cycle.errors.get(
                        asset_id,
                        "NO_MARKET_SNAPSHOT",
                    )
                )

                results[
                    asset_id
                ] = PreflightAssetResult(
                    asset_id=asset_id,
                    status=(
                        PreflightAssetStatus
                        .DATA_ERROR
                    ),
                    allowed=False,
                    error=error,
                )

                continue

            try:
                market_session = (
                    self.market_session_service
                    .get_session(
                        asset_id,
                        at=(
                            market_snapshot
                            .received_at
                        ),
                    )
                )

            except Exception as exc:
                results[
                    asset_id
                ] = PreflightAssetResult(
                    asset_id=asset_id,
                    status=(
                        PreflightAssetStatus
                        .SESSION_ERROR
                    ),
                    allowed=False,
                    error=(
                        f"{type(exc).__name__}: "
                        f"{exc}"
                    ),
                    data_quality=str(
                        enum_value(
                            market_snapshot
                            .data_quality
                        )
                    ),
                    execution_quality=str(
                        enum_value(
                            market_snapshot
                            .execution_quality
                        )
                    ),
                    provider_status=str(
                        enum_value(
                            market_snapshot
                            .provider_status
                        )
                    ),
                    quote_age_seconds=(
                        market_snapshot
                        .quote_age_seconds
                    ),
                )

                continue

            order = self._probe_order(
                asset_id
            )

            policy = self.policy.evaluate(
                order=order,
                market_snapshot=(
                    market_snapshot
                ),
                market_session=(
                    market_session
                ),
            )

            reason = (
                None
                if policy.rejection_reason
                is None
                else str(
                    enum_value(
                        policy.rejection_reason
                    )
                )
            )

            results[
                asset_id
            ] = PreflightAssetResult(
                asset_id=asset_id,
                status=(
                    PreflightAssetStatus.READY
                    if policy.allowed
                    else PreflightAssetStatus.BLOCKED
                ),
                allowed=bool(
                    policy.allowed
                ),
                rejection_reason=reason,
                data_quality=str(
                    enum_value(
                        market_snapshot
                        .data_quality
                    )
                ),
                execution_quality=str(
                    enum_value(
                        market_snapshot
                        .execution_quality
                    )
                ),
                provider_status=str(
                    enum_value(
                        market_snapshot
                        .provider_status
                    )
                ),
                session_state=str(
                    enum_value(
                        market_session.state
                    )
                ),
                session_quality=str(
                    enum_value(
                        market_session
                        .session_quality
                    )
                ),
                quote_age_seconds=(
                    market_snapshot
                    .quote_age_seconds
                ),
                labels=tuple(
                    policy.labels
                ),
            )

        return PreflightCycleResult(
            results=MappingProxyType(
                dict(results)
            ),
            market_data_errors=(
                MappingProxyType(
                    dict(
                        market_cycle.errors
                    )
                )
            ),
            duration_seconds=float(
                market_cycle.duration_seconds
            ),
            timed_out=bool(
                market_cycle.timed_out
            ),
        )


def build_live_preflight(
    *,
    paper_mode=PaperMode.REALISTIC_PAPER,
    clock=None,
    cycle_timeout_seconds=20.0,
    stale_after_seconds=120.0,
    request_timeout_seconds=10.0,
    per_asset_timeout_seconds=8.0,
    max_workers=5,
):
    clock = (
        clock
        or SystemClock()
    )

    provider = DataProvider(
        clock=clock,
        request_timeout_seconds=(
            request_timeout_seconds
        ),
    )

    market_data_service = (
        ParallelMarketDataService(
            provider,
            clock=clock,
            cycle_timeout_seconds=(
                cycle_timeout_seconds
            ),
            stale_after_seconds=(
                stale_after_seconds
            ),
            per_asset_timeout_seconds=(
                per_asset_timeout_seconds
            ),
            max_workers=max_workers,
        )
    )

    market_session_service = (
        MarketSessionService()
    )

    return RealisticLivePreflight(
        market_data_service=(
            market_data_service
        ),
        market_session_service=(
            market_session_service
        ),
        clock=clock,
        paper_mode=paper_mode,
    )
