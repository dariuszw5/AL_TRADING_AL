from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Callable, Mapping

from src.core.clock import Clock, SystemClock

from .models import (
    BrokerResult,
    ExecutionProfile,
    Order,
    OrderIntent,
    OrderSide,
    OrderStatus,
    PaperMode,
    Position,
    PositionStatus,
)


class RuntimeAssetStatus(
    str,
    Enum,
):
    HOLD = "HOLD"
    FILLED = "FILLED"
    REJECTED = "REJECTED"
    EXIT_PENDING = "EXIT_PENDING"

    DATA_ERROR = "DATA_ERROR"
    SESSION_ERROR = "SESSION_ERROR"
    DECISION_ERROR = "DECISION_ERROR"

    POSITION_ALREADY_OPEN = (
        "POSITION_ALREADY_OPEN"
    )

    NO_POSITION = "NO_POSITION"


@dataclass(frozen=True)
class ExecutionDecision:
    side: OrderSide
    intent: OrderIntent
    quantity: float

    stop_loss: float | None = None
    take_profit: float | None = None

    exit_reason: str | None = None
    signal_reference: str | None = None

    def __post_init__(self):
        if self.quantity <= 0:
            raise ValueError(
                "quantity must be positive"
            )

        if (
            self.intent
            is OrderIntent.EXIT
            and not self.exit_reason
        ):
            raise ValueError(
                "EXIT decision requires "
                "exit_reason"
            )


@dataclass(frozen=True)
class RuntimeAssetResult:
    asset_id: str
    status: RuntimeAssetStatus

    broker_result: BrokerResult | None = None

    error: str | None = None

    market_snapshot: object | None = None
    market_session: object | None = None


@dataclass(frozen=True)
class RuntimeCycleResult:
    results: Mapping[
        str,
        RuntimeAssetResult,
    ]

    market_data_errors: Mapping[
        str,
        str,
    ]

    duration_seconds: float
    timed_out: bool


DecisionProvider = Callable[
    ...,
    ExecutionDecision | None,
]


class RealisticPaperRuntime:
    """
    Isolated REALISTIC_V2 orchestration.

    This class intentionally does not use:
    - AgentLoop
    - AgentEngine
    - TradingEngine
    - LiveStateStore

    Persistence and legacy-strategy adapters are
    separate integration steps.
    """

    def __init__(
        self,
        *,
        market_data_service,
        market_session_service,
        broker,
        decision_provider: DecisionProvider,
        clock: Clock | None = None,
        paper_mode: PaperMode = (
            PaperMode.REALISTIC_PAPER
        ),
    ):
        self.market_data_service = (
            market_data_service
        )

        self.market_session_service = (
            market_session_service
        )

        self.broker = broker
        self.decision_provider = (
            decision_provider
        )

        self.clock = (
            clock
            or SystemClock()
        )

        self.paper_mode = paper_mode

        self.positions: dict[
            str,
            Position,
        ] = {}

    @staticmethod
    def _snapshot_identity(
        snapshot,
    ) -> str:
        timestamp = (
            snapshot.provider_timestamp
            or snapshot.received_at
        )

        return timestamp.isoformat()

    def _client_order_id(
        self,
        *,
        asset_id: str,
        snapshot,
        decision: ExecutionDecision,
    ) -> str:
        payload = {
            "asset_id": asset_id,
            "snapshot": (
                self._snapshot_identity(
                    snapshot
                )
            ),
            "side": decision.side.value,
            "intent": (
                decision.intent.value
            ),
            "quantity": decision.quantity,
            "stop_loss": (
                decision.stop_loss
            ),
            "take_profit": (
                decision.take_profit
            ),
            "exit_reason": (
                decision.exit_reason
            ),
            "signal_reference": (
                decision.signal_reference
            ),
            "paper_mode": (
                self.paper_mode.value
            ),
            "execution_profile": (
                ExecutionProfile
                .REALISTIC_V2
                .value
            ),
        }

        encoded = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

        digest = hashlib.sha256(
            encoded
        ).hexdigest()[:24]

        return (
            f"rv2-{asset_id}-{digest}"
        )

    def _make_order(
        self,
        *,
        asset_id,
        snapshot,
        decision,
    ):
        client_order_id = (
            self._client_order_id(
                asset_id=asset_id,
                snapshot=snapshot,
                decision=decision,
            )
        )

        return Order(
            order_id=(
                f"ord-{client_order_id}"
            ),
            client_order_id=(
                client_order_id
            ),
            asset_id=asset_id,
            side=decision.side,
            quantity=decision.quantity,
            intent=decision.intent,
            created_at=self.clock.now(),
            execution_profile=(
                ExecutionProfile
                .REALISTIC_V2
            ),
            paper_mode=self.paper_mode,
            signal_reference=(
                decision.signal_reference
            ),
            requested_exit_reason=(
                decision.exit_reason
            ),
            stop_loss=(
                decision.stop_loss
            ),
            take_profit=(
                decision.take_profit
            ),
        )

    @staticmethod
    def _runtime_status(
        broker_result,
    ):
        if (
            broker_result.status
            is OrderStatus.FILLED
        ):
            return (
                RuntimeAssetStatus.FILLED
            )

        if (
            broker_result.status
            is OrderStatus.EXIT_PENDING
        ):
            return (
                RuntimeAssetStatus.EXIT_PENDING
            )

        return (
            RuntimeAssetStatus.REJECTED
        )

    def _update_position(
        self,
        asset_id,
        broker_result,
    ):
        position = (
            broker_result.position
        )

        if position is None:
            return

        if (
            position.status
            is PositionStatus.CLOSED
        ):
            self.positions.pop(
                asset_id,
                None,
            )

            return

        self.positions[
            asset_id
        ] = position

    def _process_asset(
        self,
        *,
        asset_id,
        snapshot,
    ):
        try:
            market_session = (
                self.market_session_service
                .get_session(
                    asset_id,
                    at=snapshot.received_at,
                )
            )

        except Exception as exc:
            return RuntimeAssetResult(
                asset_id=asset_id,
                status=(
                    RuntimeAssetStatus
                    .SESSION_ERROR
                ),
                error=(
                    f"{type(exc).__name__}: "
                    f"{exc}"
                ),
                market_snapshot=snapshot,
            )

        current_position = (
            self.positions.get(
                asset_id
            )
        )

        try:
            decision = (
                self.decision_provider(
                    asset_id=asset_id,
                    snapshot=snapshot,
                    position=current_position,
                )
            )

        except Exception as exc:
            return RuntimeAssetResult(
                asset_id=asset_id,
                status=(
                    RuntimeAssetStatus
                    .DECISION_ERROR
                ),
                error=(
                    f"{type(exc).__name__}: "
                    f"{exc}"
                ),
                market_snapshot=snapshot,
                market_session=(
                    market_session
                ),
            )

        if decision is None:
            return RuntimeAssetResult(
                asset_id=asset_id,
                status=(
                    RuntimeAssetStatus.HOLD
                ),
                market_snapshot=snapshot,
                market_session=(
                    market_session
                ),
            )

        if not isinstance(
            decision,
            ExecutionDecision,
        ):
            return RuntimeAssetResult(
                asset_id=asset_id,
                status=(
                    RuntimeAssetStatus
                    .DECISION_ERROR
                ),
                error=(
                    "decision_provider returned "
                    "non-ExecutionDecision"
                ),
                market_snapshot=snapshot,
                market_session=(
                    market_session
                ),
            )

        if (
            decision.intent
            is OrderIntent.ENTRY
            and current_position
            is not None
        ):
            return RuntimeAssetResult(
                asset_id=asset_id,
                status=(
                    RuntimeAssetStatus
                    .POSITION_ALREADY_OPEN
                ),
                market_snapshot=snapshot,
                market_session=(
                    market_session
                ),
            )

        if (
            decision.intent
            is OrderIntent.EXIT
            and current_position
            is None
        ):
            return RuntimeAssetResult(
                asset_id=asset_id,
                status=(
                    RuntimeAssetStatus
                    .NO_POSITION
                ),
                market_snapshot=snapshot,
                market_session=(
                    market_session
                ),
            )

        order = self._make_order(
            asset_id=asset_id,
            snapshot=snapshot,
            decision=decision,
        )

        broker_result = (
            self.broker.submit_order(
                order,
                market_snapshot=snapshot,
                market_session=(
                    market_session
                ),
                position=current_position,
            )
        )

        self._update_position(
            asset_id,
            broker_result,
        )

        return RuntimeAssetResult(
            asset_id=asset_id,
            status=self._runtime_status(
                broker_result
            ),
            broker_result=(
                broker_result
            ),
            market_snapshot=snapshot,
            market_session=(
                market_session
            ),
        )

    def run_cycle(
        self,
        asset_ids,
    ) -> RuntimeCycleResult:
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
            snapshot = (
                market_cycle.snapshots.get(
                    asset_id
                )
            )

            if snapshot is None:
                error = (
                    market_cycle.errors.get(
                        asset_id,
                        "NO_MARKET_SNAPSHOT",
                    )
                )

                results[
                    asset_id
                ] = RuntimeAssetResult(
                    asset_id=asset_id,
                    status=(
                        RuntimeAssetStatus
                        .DATA_ERROR
                    ),
                    error=error,
                )

                continue

            results[
                asset_id
            ] = self._process_asset(
                asset_id=asset_id,
                snapshot=snapshot,
            )

        return RuntimeCycleResult(
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
