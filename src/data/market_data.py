from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from math import isfinite
from typing import Any

from src.core.clock import ensure_utc_aware


class DataQuality(str, Enum):
    REALTIME = "REALTIME"
    DELAYED = "DELAYED"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"
    UNRELIABLE = "UNRELIABLE"


class ExecutionQuality(str, Enum):
    REAL_BOOK = "REAL_BOOK"
    DERIVED_SPREAD = "DERIVED_SPREAD"
    SIMULATED_SPREAD = "SIMULATED_SPREAD"
    UNTRADEABLE = "UNTRADEABLE"


class ProviderStatus(str, Enum):
    CONNECTED = "CONNECTED"
    DEGRADED = "DEGRADED"
    DISCONNECTED = "DISCONNECTED"
    RATE_LIMITED = "RATE_LIMITED"
    ERROR = "ERROR"


def _positive_optional(
    value: float | None,
    name: str,
):
    if value is None:
        return

    if not isfinite(value) or value <= 0.0:
        raise ValueError(
            f"{name} must be positive and finite"
        )


@dataclass(frozen=True)
class NormalizedCandle:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

    def __post_init__(self):
        object.__setattr__(
            self,
            "timestamp",
            ensure_utc_aware(self.timestamp),
        )

        values = (
            self.open,
            self.high,
            self.low,
            self.close,
            self.volume,
        )

        if not all(
            isfinite(value)
            for value in values
        ):
            raise ValueError(
                "Candle values must be finite"
            )

        if min(
            self.open,
            self.high,
            self.low,
            self.close,
        ) <= 0.0:
            raise ValueError(
                "OHLC values must be positive"
            )

        if self.volume < 0.0:
            raise ValueError(
                "Volume cannot be negative"
            )

        if self.low > min(
            self.open,
            self.close,
        ):
            raise ValueError(
                "Low cannot exceed open/close"
            )

        if self.high < max(
            self.open,
            self.close,
        ):
            raise ValueError(
                "High cannot be below open/close"
            )

        if self.low > self.high:
            raise ValueError(
                "Low cannot exceed high"
            )

    @classmethod
    def from_legacy(
        cls,
        candle: Any,
    ):
        return cls(
            timestamp=datetime.fromtimestamp(
                candle.timestamp / 1000.0,
                tz=timezone.utc,
            ),
            open=float(candle.open),
            high=float(candle.high),
            low=float(candle.low),
            close=float(candle.close),
            volume=float(candle.volume),
        )


@dataclass(frozen=True)
class MarketSnapshot:
    asset_id: str

    bid: float | None
    ask: float | None
    last: float | None

    provider_timestamp: datetime | None
    received_at: datetime

    data_quality: DataQuality
    delayed: bool | None
    quote_age_seconds: float | None

    provider_status: ProviderStatus
    execution_quality: ExecutionQuality

    metadata: tuple[
        tuple[str, str],
        ...
    ] = ()

    def __post_init__(self):
        if not self.asset_id.strip():
            raise ValueError(
                "asset_id is required"
            )

        object.__setattr__(
            self,
            "received_at",
            ensure_utc_aware(
                self.received_at
            ),
        )

        if self.provider_timestamp is not None:
            object.__setattr__(
                self,
                "provider_timestamp",
                ensure_utc_aware(
                    self.provider_timestamp
                ),
            )

        _positive_optional(
            self.bid,
            "bid",
        )
        _positive_optional(
            self.ask,
            "ask",
        )
        _positive_optional(
            self.last,
            "last",
        )

        if (
            self.bid is not None
            and self.ask is not None
            and self.bid > self.ask
        ):
            raise ValueError(
                "bid cannot exceed ask"
            )

        if (
            self.quote_age_seconds is not None
            and (
                not isfinite(
                    self.quote_age_seconds
                )
                or self.quote_age_seconds < 0.0
            )
        ):
            raise ValueError(
                "quote_age_seconds must be "
                "non-negative and finite"
            )

        if (
            self.execution_quality
            is ExecutionQuality.REAL_BOOK
            and (
                self.bid is None
                or self.ask is None
            )
        ):
            raise ValueError(
                "REAL_BOOK requires bid and ask"
            )

        if (
            self.data_quality
            is DataQuality.REALTIME
            and self.delayed is True
        ):
            raise ValueError(
                "REALTIME cannot be delayed"
            )

        if (
            self.data_quality
            in {
                DataQuality.DELAYED,
                DataQuality.STALE,
            }
            and self.delayed is False
        ):
            raise ValueError(
                "DELAYED/STALE cannot have "
                "delayed=False"
            )


@dataclass(frozen=True)
class ProviderHealth:
    asset_id: str
    provider: str
    status: ProviderStatus
    checked_at: datetime

    last_success_at: datetime | None = None
    latency_ms: float | None = None
    consecutive_failures: int = 0
    last_error: str | None = None

    def __post_init__(self):
        object.__setattr__(
            self,
            "checked_at",
            ensure_utc_aware(
                self.checked_at
            ),
        )

        if self.last_success_at is not None:
            object.__setattr__(
                self,
                "last_success_at",
                ensure_utc_aware(
                    self.last_success_at
                ),
            )

        if self.latency_ms is not None:
            if (
                not isfinite(self.latency_ms)
                or self.latency_ms < 0.0
            ):
                raise ValueError(
                    "latency_ms must be "
                    "non-negative and finite"
                )

        if self.consecutive_failures < 0:
            raise ValueError(
                "consecutive_failures "
                "cannot be negative"
            )


def normalize_candles(
    candles,
) -> tuple[NormalizedCandle, ...]:
    result = []
    previous_timestamp = None

    for candle in candles:
        normalized = (
            candle
            if isinstance(
                candle,
                NormalizedCandle,
            )
            else NormalizedCandle.from_legacy(
                candle
            )
        )

        if (
            previous_timestamp is not None
            and normalized.timestamp
            <= previous_timestamp
        ):
            raise ValueError(
                "Duplicate or out-of-order "
                "candle timestamp"
            )

        previous_timestamp = (
            normalized.timestamp
        )

        result.append(normalized)

    return tuple(result)


def validate_legacy_candles(
    candles,
):
    normalize_candles(candles)
    return candles


def classify_data_quality(
    *,
    provider_timestamp: datetime | None,
    received_at: datetime,
    delay_hint_seconds: float | None,
    stale_after_seconds: float,
):
    received_at = ensure_utc_aware(
        received_at
    )

    if stale_after_seconds <= 0.0:
        raise ValueError(
            "stale_after_seconds must "
            "be positive"
        )

    if provider_timestamp is None:
        return (
            DataQuality.UNKNOWN,
            None,
            None,
        )

    provider_timestamp = ensure_utc_aware(
        provider_timestamp
    )

    age = max(
        0.0,
        (
            received_at
            - provider_timestamp
        ).total_seconds(),
    )

    if age > stale_after_seconds:
        return (
            DataQuality.STALE,
            True,
            age,
        )

    if delay_hint_seconds is None:
        return (
            DataQuality.UNKNOWN,
            None,
            age,
        )

    if delay_hint_seconds < 0.0:
        raise ValueError(
            "delay_hint_seconds cannot "
            "be negative"
        )

    if delay_hint_seconds > 0.0:
        return (
            DataQuality.DELAYED,
            True,
            age,
        )

    return (
        DataQuality.REALTIME,
        False,
        age,
    )
