from __future__ import annotations

from dataclasses import dataclass
from datetime import timezone

from .models import (
    FxFreshness,
    FxFreshnessResult,
)


UNAVAILABLE_AFTER_SECONDS = (
    96.0
    * 60.0
    * 60.0
)


# Phase 09 A.12 accepted production defaults.
#
# The 2026-09-17 empirical Yahoo PLN FX probe showed:
# - median update cadence: 1 hour,
# - observed weekend market-data gap: 49 hours.
#
# A two-hour freshness threshold allows one missed hourly update
# without pretending an old Friday FX quote remains fresh through
# the weekend. Weekend continuity is provided by FX_STALE up to the
# existing 96-hour hard-unavailable boundary.
#
# Weekday and weekend values remain separate configuration fields
# even though the accepted defaults are currently equal.
PRODUCTION_WEEKDAY_MAX_FX_AGE_SECONDS = (
    2.0
    * 60.0
    * 60.0
)

PRODUCTION_WEEKEND_MAX_FX_AGE_SECONDS = (
    2.0
    * 60.0
    * 60.0
)


def _aware_utc(
    value,
    field_name,
):
    if value.tzinfo is None:
        raise ValueError(
            f"{field_name} must be timezone-aware"
        )

    return value.astimezone(
        timezone.utc
    )


@dataclass(frozen=True)
class FxFreshnessPolicy:
    """
    Production max_fx_age values are deliberately
    not frozen here.

    Boundary contract:

    age < max_fx_age
        FX_FRESH

    age >= max_fx_age and age <= 96h
        FX_STALE

    age > 96h
        FX_UNAVAILABLE
    """

    weekday_max_age_seconds: float
    weekend_max_age_seconds: float
    unavailable_after_seconds: float = (
        UNAVAILABLE_AFTER_SECONDS
    )

    def __post_init__(self):
        weekday = float(
            self.weekday_max_age_seconds
        )

        weekend = float(
            self.weekend_max_age_seconds
        )

        unavailable = float(
            self.unavailable_after_seconds
        )

        for name, value in (
            (
                "weekday_max_age_seconds",
                weekday,
            ),
            (
                "weekend_max_age_seconds",
                weekend,
            ),
            (
                "unavailable_after_seconds",
                unavailable,
            ),
        ):
            if value <= 0:
                raise ValueError(
                    f"{name} must be positive"
                )

        if weekday > unavailable:
            raise ValueError(
                "weekday_max_age_seconds "
                "must not exceed unavailable threshold"
            )

        if weekend > unavailable:
            raise ValueError(
                "weekend_max_age_seconds "
                "must not exceed unavailable threshold"
            )

        object.__setattr__(
            self,
            "weekday_max_age_seconds",
            weekday,
        )

        object.__setattr__(
            self,
            "weekend_max_age_seconds",
            weekend,
        )

        object.__setattr__(
            self,
            "unavailable_after_seconds",
            unavailable,
        )

    def max_age_seconds(
        self,
        now,
    ):
        now = _aware_utc(
            now,
            "now",
        )

        if now.weekday() >= 5:
            return (
                self.weekend_max_age_seconds
            )

        return (
            self.weekday_max_age_seconds
        )

    def evaluate(
        self,
        quote,
        *,
        now,
    ):
        now = _aware_utc(
            now,
            "now",
        )

        threshold = (
            self.max_age_seconds(
                now
            )
        )

        timestamp = quote.provider_timestamp

        if timestamp is None:
            return FxFreshnessResult(
                state=(
                    FxFreshness.FX_UNAVAILABLE
                ),
                age_seconds=None,
                max_age_seconds=threshold,
                reason=(
                    "FX_TIMESTAMP_UNAVAILABLE"
                ),
            )

        timestamp = _aware_utc(
            timestamp,
            "provider_timestamp",
        )

        age = (
            now
            - timestamp
        ).total_seconds()

        if age < 0:
            return FxFreshnessResult(
                state=(
                    FxFreshness.FX_UNAVAILABLE
                ),
                age_seconds=age,
                max_age_seconds=threshold,
                reason="FUTURE_FX_TIMESTAMP",
            )

        if (
            age
            > self.unavailable_after_seconds
        ):
            return FxFreshnessResult(
                state=(
                    FxFreshness.FX_UNAVAILABLE
                ),
                age_seconds=age,
                max_age_seconds=threshold,
                reason="FX_QUOTE_EXPIRED",
            )

        if age < threshold:
            return FxFreshnessResult(
                state=(
                    FxFreshness.FX_FRESH
                ),
                age_seconds=age,
                max_age_seconds=threshold,
            )

        return FxFreshnessResult(
            state=(
                FxFreshness.FX_STALE
            ),
            age_seconds=age,
            max_age_seconds=threshold,
        )

def production_fx_freshness_policy():
    """
    Return the Phase 09 accepted production freshness policy.

    Runtime integration must include the resolved threshold values
    in reproducibility metadata/config fingerprint.
    """

    return FxFreshnessPolicy(
        weekday_max_age_seconds=(
            PRODUCTION_WEEKDAY_MAX_FX_AGE_SECONDS
        ),
        weekend_max_age_seconds=(
            PRODUCTION_WEEKEND_MAX_FX_AGE_SECONDS
        ),
    )
