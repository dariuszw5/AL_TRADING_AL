from __future__ import annotations

from dataclasses import dataclass
from datetime import timezone

from .models import (
    FxSourceQuality,
)


class RealizedFxSelectionError(
    ValueError
):
    pass


def _aware_utc(
    value,
    field_name,
):
    if value.tzinfo is None:
        raise RealizedFxSelectionError(
            f"{field_name} must be timezone-aware"
        )

    return value.astimezone(
        timezone.utc
    )


def _currency(
    value,
):
    result = (
        str(value)
        .strip()
        .upper()
    )

    if not result:
        raise RealizedFxSelectionError(
            "native_currency is required"
        )

    return result


@dataclass(frozen=True)
class RealizedFxSelectionPolicy:
    """
    Deterministic realized-FX evidence selector.

    DAILY_REFERENCE rule:

    * effective_date after close date -> never eligible
    * same-day reference -> eligible only when it was
      actually observed by the system no later than close
    * prior-date reference -> eligible as an already-existing
      daily reference even if fetched later for reconstruction

    Timestamped market quote rule:

    * provider_timestamp <= closed_at
    * use latest eligible quote
    * enforce caller-supplied max age

    Production thresholds are not frozen by this class.
    """

    market_max_age_seconds: float
    daily_reference_max_age_days: int

    nbp_provider: str = "NBP_TABLE_A"
    usdt_usd_provider: str = "COINBASE_EXCHANGE"

    def __post_init__(self):
        market_age = float(
            self.market_max_age_seconds
        )

        reference_age = int(
            self.daily_reference_max_age_days
        )

        if market_age <= 0:
            raise ValueError(
                "market_max_age_seconds must be positive"
            )

        if reference_age <= 0:
            raise ValueError(
                "daily_reference_max_age_days must be positive"
            )

        object.__setattr__(
            self,
            "market_max_age_seconds",
            market_age,
        )

        object.__setattr__(
            self,
            "daily_reference_max_age_days",
            reference_age,
        )

    def _select_daily_reference(
        self,
        pair,
        *,
        closed_at,
        quotes,
    ):
        matching = [
            quote
            for quote in quotes
            if (
                quote.pair == pair
                and quote.provider == self.nbp_provider
                and quote.source_quality
                is FxSourceQuality.DAILY_REFERENCE
            )
        ]

        if not matching:
            raise RealizedFxSelectionError(
                "NBP_REFERENCE_UNAVAILABLE:"
                + pair
            )

        complete = [
            quote
            for quote in matching
            if (
                quote.table
                and quote.effective_date is not None
            )
        ]

        if not complete:
            raise RealizedFxSelectionError(
                "DAILY_REFERENCE_METADATA_INCOMPLETE:"
                + pair
            )

        close_date = closed_at.date()

        eligible = []

        for quote in complete:
            if quote.effective_date > close_date:
                continue

            if (
                quote.provider_timestamp is not None
                and quote.provider_timestamp > closed_at
            ):
                continue

            if (
                quote.effective_date == close_date
                and quote.observed_at > closed_at
            ):
                continue

            eligible.append(
                quote
            )

        if not eligible:
            raise RealizedFxSelectionError(
                "SAFE_NBP_REFERENCE_UNAVAILABLE_AT_CLOSE:"
                + pair
            )

        latest_date = max(
            quote.effective_date
            for quote in eligible
        )

        latest = [
            quote
            for quote in eligible
            if quote.effective_date == latest_date
        ]

        if len(latest) != 1:
            raise RealizedFxSelectionError(
                "AMBIGUOUS_DAILY_REFERENCE:"
                + pair
            )

        selected = latest[0]

        age_days = (
            close_date
            - selected.effective_date
        ).days

        if (
            age_days
            > self.daily_reference_max_age_days
        ):
            raise RealizedFxSelectionError(
                "DAILY_REFERENCE_TOO_OLD:"
                + pair
            )

        return selected

    def _select_market_quote(
        self,
        pair,
        *,
        provider,
        closed_at,
        quotes,
    ):
        matching = [
            quote
            for quote in quotes
            if (
                quote.pair == pair
                and quote.provider == provider
                and quote.source_quality
                is FxSourceQuality.LIVE
                and quote.provider_timestamp is not None
            )
        ]

        if not matching:
            raise RealizedFxSelectionError(
                "MARKET_FX_SOURCE_UNAVAILABLE:"
                + pair
            )

        eligible = [
            quote
            for quote in matching
            if quote.provider_timestamp <= closed_at
        ]

        if not eligible:
            raise RealizedFxSelectionError(
                "MARKET_FX_QUOTE_UNAVAILABLE_AT_CLOSE:"
                + pair
            )

        latest_timestamp = max(
            quote.provider_timestamp
            for quote in eligible
        )

        latest = [
            quote
            for quote in eligible
            if quote.provider_timestamp
            == latest_timestamp
        ]

        if len(latest) != 1:
            raise RealizedFxSelectionError(
                "AMBIGUOUS_MARKET_FX_QUOTE:"
                + pair
            )

        selected = latest[0]

        age_seconds = (
            closed_at
            - selected.provider_timestamp
        ).total_seconds()

        if (
            age_seconds
            > self.market_max_age_seconds
        ):
            raise RealizedFxSelectionError(
                "MARKET_FX_QUOTE_TOO_OLD:"
                + pair
            )

        return selected

    def select(
        self,
        *,
        closed_at,
        native_currency,
        quotes,
    ):
        closed_at = _aware_utc(
            closed_at,
            "closed_at",
        )

        source = _currency(
            native_currency
        )

        quotes = tuple(
            quotes
        )

        if source == "PLN":
            return ()

        if source == "USD":
            return (
                self._select_daily_reference(
                    "USDPLN",
                    closed_at=closed_at,
                    quotes=quotes,
                ),
            )

        if source == "EUR":
            return (
                self._select_daily_reference(
                    "EURPLN",
                    closed_at=closed_at,
                    quotes=quotes,
                ),
            )

        if source == "USDT":
            usdt_usd = self._select_market_quote(
                "USDTUSD",
                provider=self.usdt_usd_provider,
                closed_at=closed_at,
                quotes=quotes,
            )

            usd_pln = self._select_daily_reference(
                "USDPLN",
                closed_at=closed_at,
                quotes=quotes,
            )

            return (
                usdt_usd,
                usd_pln,
            )

        raise RealizedFxSelectionError(
            "NO_REALIZED_FX_PATH:"
            f"{source}→PLN"
        )
