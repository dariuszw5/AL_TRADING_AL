from __future__ import annotations

from src.core.clock import (
    Clock,
    SystemClock,
)

from .models import (
    FxConversionResult,
    FxFreshness,
    FxPath,
)


FX_CONVERSION_COST_LIMITATION = (
    "KNOWN_LIMITATION: "
    "FX_CONVERSION_COST_NOT_MODELLED"
)


class CurrencyConverter:
    """
    Deterministic, fail-closed PLN converter.

    Supported explicit paths:

    PLN
    USD -> PLN
    EUR -> PLN
    USDT -> USD -> PLN

    No implicit inversion.
    No implicit USDT == USD.
    """

    def __init__(
        self,
        *,
        freshness_policy,
        clock: Clock | None = None,
    ):
        self.freshness_policy = (
            freshness_policy
        )

        self.clock = (
            clock
            or SystemClock()
        )

    @staticmethod
    def _quote_map(
        quotes,
    ):
        result = {}

        for quote in quotes:
            pair = quote.pair

            if pair in result:
                raise ValueError(
                    "duplicate FX quote "
                    f"for {pair}"
                )

            result[pair] = quote

        return result

    @staticmethod
    def _path_for(
        source_currency,
    ):
        source = (
            str(source_currency)
            .strip()
            .upper()
        )

        if source == "PLN":
            return FxPath(
                ("PLN",)
            )

        if source == "USD":
            return FxPath(
                (
                    "USD",
                    "PLN",
                )
            )

        if source == "EUR":
            return FxPath(
                (
                    "EUR",
                    "PLN",
                )
            )

        if source == "USDT":
            return FxPath(
                (
                    "USDT",
                    "USD",
                    "PLN",
                )
            )

        return FxPath(
            (
                source,
                "PLN",
            )
        )

    @staticmethod
    def _pairs_for(
        path,
    ):
        currencies = path.currencies

        return tuple(
            currencies[index]
            + currencies[index + 1]
            for index
            in range(
                len(currencies) - 1
            )
        )

    @staticmethod
    def _limitations_for(
        path,
    ):
        if path.text == "PLN":
            return ()

        return (
            FX_CONVERSION_COST_LIMITATION,
        )

    def _unavailable(
        self,
        *,
        amount,
        source,
        path,
        reason,
        legs=(),
        age_seconds=None,
    ):
        return FxConversionResult(
            source_amount=float(amount),
            source_currency=source,
            target_currency="PLN",
            converted_amount=None,
            fx_path=path,
            freshness=(
                FxFreshness.FX_UNAVAILABLE
            ),
            quote_age_seconds=age_seconds,
            legs=tuple(legs),
            limitations=(
                self._limitations_for(
                    path
                )
            ),
            unavailable_reason=reason,
        )

    def convert_to_pln(
        self,
        amount,
        source_currency,
        quotes,
    ):
        amount = float(
            amount
        )

        source = (
            str(source_currency)
            .strip()
            .upper()
        )

        if not source:
            raise ValueError(
                "source currency is required"
            )

        path = self._path_for(
            source
        )

        if source == "PLN":
            return FxConversionResult(
                source_amount=amount,
                source_currency="PLN",
                target_currency="PLN",
                converted_amount=amount,
                fx_path=path,
                freshness=(
                    FxFreshness.FX_FRESH
                ),
                quote_age_seconds=0.0,
                legs=(),
                limitations=(),
            )

        if source not in {
            "USD",
            "EUR",
            "USDT",
        }:
            return self._unavailable(
                amount=amount,
                source=source,
                path=path,
                reason=(
                    "NO_FX_PATH:"
                    + path.text
                ),
            )

        quote_map = self._quote_map(
            quotes
        )

        legs = []

        for pair in self._pairs_for(
            path
        ):
            quote = quote_map.get(
                pair
            )

            if quote is None:
                return self._unavailable(
                    amount=amount,
                    source=source,
                    path=path,
                    reason=(
                        "MISSING_FX_LEG:"
                        + pair
                    ),
                    legs=legs,
                )

            legs.append(
                quote
            )

        now = self.clock.now()

        evaluations = tuple(
            self.freshness_policy.evaluate(
                quote,
                now=now,
            )
            for quote
            in legs
        )

        ages = tuple(
            result.age_seconds
            for result
            in evaluations
            if result.age_seconds is not None
        )

        max_age = (
            max(ages)
            if ages
            else None
        )

        unavailable = next(
            (
                result
                for result
                in evaluations
                if (
                    result.state
                    is FxFreshness.FX_UNAVAILABLE
                )
            ),
            None,
        )

        if unavailable is not None:
            return self._unavailable(
                amount=amount,
                source=source,
                path=path,
                reason=(
                    unavailable.reason
                    or "FX_UNAVAILABLE"
                ),
                legs=legs,
                age_seconds=max_age,
            )

        freshness = (
            FxFreshness.FX_STALE
            if any(
                result.state
                is FxFreshness.FX_STALE
                for result
                in evaluations
            )
            else FxFreshness.FX_FRESH
        )

        converted = amount

        for quote in legs:
            converted *= quote.rate

        return FxConversionResult(
            source_amount=amount,
            source_currency=source,
            target_currency="PLN",
            converted_amount=converted,
            fx_path=path,
            freshness=freshness,
            quote_age_seconds=max_age,
            legs=tuple(legs),
            limitations=(
                self._limitations_for(
                    path
                )
            ),
        )
