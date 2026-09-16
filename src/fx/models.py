from __future__ import annotations

from dataclasses import dataclass
from datetime import (
    date,
    datetime,
    timezone,
)
from enum import Enum


class FxSourceQuality(str, Enum):
    LIVE = "LIVE"
    DAILY_REFERENCE = "DAILY_REFERENCE"
    STALE_PRONE = "STALE_PRONE"


class FxFreshness(str, Enum):
    FX_FRESH = "FX_FRESH"
    FX_STALE = "FX_STALE"
    FX_UNAVAILABLE = "FX_UNAVAILABLE"


def _currency_code(
    value,
):
    result = (
        str(value)
        .strip()
        .upper()
    )

    if not result:
        raise ValueError(
            "currency code is required"
        )

    return result


def _normalize_datetime(
    value,
    field_name,
):
    if value is None:
        return None

    if value.tzinfo is None:
        raise ValueError(
            f"{field_name} must be timezone-aware"
        )

    return value.astimezone(
        timezone.utc
    )


@dataclass(frozen=True)
class FxPath:
    currencies: tuple[str, ...]

    def __post_init__(self):
        normalized = tuple(
            _currency_code(value)
            for value
            in self.currencies
        )

        if not normalized:
            raise ValueError(
                "FX path cannot be empty"
            )

        object.__setattr__(
            self,
            "currencies",
            normalized,
        )

    @property
    def text(self):
        return "→".join(
            self.currencies
        )


@dataclass(frozen=True)
class FxQuote:
    base_currency: str
    quote_currency: str
    rate: float
    provider: str
    provider_timestamp: datetime | None
    observed_at: datetime
    source_quality: FxSourceQuality
    bid: float | None = None
    ask: float | None = None
    table: str | None = None
    effective_date: date | None = None
    labels: tuple[str, ...] = ()

    def __post_init__(self):
        base = _currency_code(
            self.base_currency
        )

        quote = _currency_code(
            self.quote_currency
        )

        if base == quote:
            raise ValueError(
                "FX quote must cross currencies"
            )

        rate = float(
            self.rate
        )

        if rate <= 0:
            raise ValueError(
                "rate must be positive"
            )

        provider = str(
            self.provider
        ).strip()

        if not provider:
            raise ValueError(
                "provider is required"
            )

        provider_timestamp = (
            _normalize_datetime(
                self.provider_timestamp,
                "provider_timestamp",
            )
        )

        observed_at = _normalize_datetime(
            self.observed_at,
            "observed_at",
        )

        bid = (
            None
            if self.bid is None
            else float(self.bid)
        )

        ask = (
            None
            if self.ask is None
            else float(self.ask)
        )

        if bid is not None and bid <= 0:
            raise ValueError(
                "bid must be positive"
            )

        if ask is not None and ask <= 0:
            raise ValueError(
                "ask must be positive"
            )

        if (
            bid is not None
            and ask is not None
            and bid > ask
        ):
            raise ValueError(
                "bid cannot exceed ask"
            )

        object.__setattr__(
            self,
            "base_currency",
            base,
        )

        object.__setattr__(
            self,
            "quote_currency",
            quote,
        )

        object.__setattr__(
            self,
            "rate",
            rate,
        )

        object.__setattr__(
            self,
            "provider",
            provider,
        )

        object.__setattr__(
            self,
            "provider_timestamp",
            provider_timestamp,
        )

        object.__setattr__(
            self,
            "observed_at",
            observed_at,
        )

        object.__setattr__(
            self,
            "bid",
            bid,
        )

        object.__setattr__(
            self,
            "ask",
            ask,
        )

        object.__setattr__(
            self,
            "labels",
            tuple(
                str(value)
                for value
                in self.labels
            ),
        )

    @property
    def pair(self):
        return (
            self.base_currency
            + self.quote_currency
        )


@dataclass(frozen=True)
class FxFreshnessResult:
    state: FxFreshness
    age_seconds: float | None
    max_age_seconds: float
    reason: str | None = None


@dataclass(frozen=True)
class FxConversionResult:
    source_amount: float
    source_currency: str
    target_currency: str
    converted_amount: float | None
    fx_path: FxPath
    freshness: FxFreshness
    quote_age_seconds: float | None
    legs: tuple[FxQuote, ...]
    limitations: tuple[str, ...] = ()
    unavailable_reason: str | None = None

    @property
    def available(self):
        return (
            self.converted_amount
            is not None
            and self.freshness
            is not FxFreshness.FX_UNAVAILABLE
        )
