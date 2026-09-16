from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

from src.data.market_data import ExecutionQuality


class ExecutionProfile(str, Enum):
    LEGACY_V1 = "LEGACY_V1"
    REALISTIC_V2 = "REALISTIC_V2"


class PaperMode(str, Enum):
    REALISTIC_PAPER = "realistic_paper"
    RESEARCH_PAPER = "research_paper"


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderIntent(str, Enum):
    ENTRY = "ENTRY"
    EXIT = "EXIT"


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    REJECTED = "REJECTED"
    EXIT_PENDING = "EXIT_PENDING"


class PositionSide(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class PositionStatus(str, Enum):
    OPEN = "OPEN"
    EXIT_PENDING = "EXIT_PENDING"
    CLOSED = "CLOSED"


class RejectionReason(str, Enum):
    PROFILE_NOT_ALLOWED = "PROFILE_NOT_ALLOWED"
    MARKET_CLOSED = "MARKET_CLOSED"
    STALE_DATA = "STALE_DATA"
    DELAYED_DATA = "DELAYED_DATA"
    UNTRADEABLE = "UNTRADEABLE"
    SHORT_NOT_SUPPORTED = "SHORT_NOT_SUPPORTED"
    LONG_NOT_SUPPORTED = "LONG_NOT_SUPPORTED"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    SESSION_UNAVAILABLE = "SESSION_UNAVAILABLE"
    IDEMPOTENCY_CONFLICT = "IDEMPOTENCY_CONFLICT"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"
    SIMULATED_SPREAD_NOT_ALLOWED = (
        "SIMULATED_SPREAD_NOT_ALLOWED"
    )
    DERIVED_SPREAD_NOT_VALIDATED = (
        "DERIVED_SPREAD_NOT_VALIDATED"
    )
    QUOTE_UNAVAILABLE = "QUOTE_UNAVAILABLE"
    INVALID_ORDER = "INVALID_ORDER"


def _require_aware_utc(
    value: datetime,
    field_name: str,
):
    if value.tzinfo is None:
        raise ValueError(
            f"{field_name} must be timezone-aware"
        )

    normalized = value.astimezone(
        timezone.utc
    )

    if normalized.utcoffset() != timezone.utc.utcoffset(
        normalized
    ):
        raise ValueError(
            f"{field_name} must normalize to UTC"
        )


@dataclass(frozen=True)
class Order:
    order_id: str
    client_order_id: str
    asset_id: str
    side: OrderSide
    quantity: float
    intent: OrderIntent
    created_at: datetime
    execution_profile: ExecutionProfile
    paper_mode: PaperMode
    signal_reference: str | None = None
    requested_exit_reason: str | None = None
    stop_loss: float | None = None
    take_profit: float | None = None

    def __post_init__(self):
        if not self.order_id:
            raise ValueError(
                "order_id is required"
            )

        if not self.client_order_id:
            raise ValueError(
                "client_order_id is required"
            )

        if not self.asset_id:
            raise ValueError(
                "asset_id is required"
            )

        if self.quantity <= 0:
            raise ValueError(
                "quantity must be positive"
            )

        _require_aware_utc(
            self.created_at,
            "created_at",
        )


@dataclass(frozen=True)
class Execution:
    execution_id: str
    order_id: str
    asset_id: str
    side: OrderSide
    quantity: float
    reference_price: float
    execution_price: float
    bid: float
    ask: float
    spread: float
    slippage: float
    fee: float
    provider_timestamp: datetime | None
    execution_timestamp: datetime
    data_quality: object
    execution_quality: ExecutionQuality
    session_quality: object
    paper_mode: PaperMode
    short_label: str | None
    trigger_reason: str | None
    pending_reason: str | None
    execution_reason: str
    labels: tuple[str, ...] = ()
    config_hash: str | None = None

    def __post_init__(self):
        _require_aware_utc(
            self.execution_timestamp,
            "execution_timestamp",
        )

        if (
            self.provider_timestamp is not None
        ):
            _require_aware_utc(
                self.provider_timestamp,
                "provider_timestamp",
            )


@dataclass(frozen=True)
class Position:
    position_id: str
    asset_id: str
    side: PositionSide
    quantity: float
    entry_execution_id: str
    entry_price: float
    stop_loss: float | None
    take_profit: float | None
    opened_at: datetime
    short_mechanism: str | None
    short_financing_model: str | None
    execution_profile: ExecutionProfile
    execution_quality_at_entry: ExecutionQuality
    status: PositionStatus
    closed_at: datetime | None = None
    exit_execution_id: str | None = None
    exit_price: float | None = None
    pending_exit_reason: str | None = None
    pending_since: datetime | None = None

    def __post_init__(self):
        if self.quantity <= 0:
            raise ValueError(
                "position quantity must be positive"
            )

        _require_aware_utc(
            self.opened_at,
            "opened_at",
        )

        if self.closed_at is not None:
            _require_aware_utc(
                self.closed_at,
                "closed_at",
            )

        if self.pending_since is not None:
            _require_aware_utc(
                self.pending_since,
                "pending_since",
            )


@dataclass(frozen=True)
class BrokerResult:
    status: OrderStatus
    order: Order
    execution: Execution | None = None
    position: Position | None = None
    rejection_reason: RejectionReason | None = None
    labels: tuple[str, ...] = ()
