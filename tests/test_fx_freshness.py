from datetime import (
    datetime,
    timedelta,
    timezone,
)

import pytest

from src.fx.freshness import (
    FxFreshnessPolicy,
)
from src.fx.models import (
    FxFreshness,
    FxQuote,
    FxSourceQuality,
)


MONDAY = datetime(
    2026,
    9,
    14,
    12,
    0,
    tzinfo=timezone.utc,
)

SATURDAY = datetime(
    2026,
    9,
    19,
    12,
    0,
    tzinfo=timezone.utc,
)


def make_quote(
    provider_timestamp,
    *,
    observed_at=MONDAY,
):
    return FxQuote(
        base_currency="USD",
        quote_currency="PLN",
        rate=3.75,
        provider="TEST",
        provider_timestamp=provider_timestamp,
        observed_at=observed_at,
        source_quality=(
            FxSourceQuality.STALE_PRONE
        ),
    )


def policy():
    # TEST-ONLY values.
    # Production thresholds remain unfrozen.
    return FxFreshnessPolicy(
        weekday_max_age_seconds=900.0,
        weekend_max_age_seconds=7200.0,
    )


def test_younger_than_weekday_threshold_is_fresh():
    result = policy().evaluate(
        make_quote(
            MONDAY
            - timedelta(
                seconds=899,
            )
        ),
        now=MONDAY,
    )

    assert result.state is FxFreshness.FX_FRESH
    assert result.age_seconds == 899.0


def test_exact_freshness_boundary_is_stale():
    result = policy().evaluate(
        make_quote(
            MONDAY
            - timedelta(
                seconds=900,
            )
        ),
        now=MONDAY,
    )

    assert result.state is FxFreshness.FX_STALE
    assert result.age_seconds == 900.0


def test_weekend_uses_separate_threshold():
    result = policy().evaluate(
        make_quote(
            SATURDAY
            - timedelta(
                seconds=3600,
            ),
            observed_at=SATURDAY,
        ),
        now=SATURDAY,
    )

    assert result.state is FxFreshness.FX_FRESH


def test_exact_weekend_threshold_is_stale():
    result = policy().evaluate(
        make_quote(
            SATURDAY
            - timedelta(
                seconds=7200,
            ),
            observed_at=SATURDAY,
        ),
        now=SATURDAY,
    )

    assert result.state is FxFreshness.FX_STALE


def test_exact_96_hours_is_stale():
    result = policy().evaluate(
        make_quote(
            MONDAY
            - timedelta(
                hours=96,
            )
        ),
        now=MONDAY,
    )

    assert result.state is FxFreshness.FX_STALE


def test_more_than_96_hours_is_unavailable():
    result = policy().evaluate(
        make_quote(
            MONDAY
            - timedelta(
                hours=96,
                seconds=1,
            )
        ),
        now=MONDAY,
    )

    assert (
        result.state
        is FxFreshness.FX_UNAVAILABLE
    )

    assert result.reason == "FX_QUOTE_EXPIRED"


def test_future_provider_timestamp_is_unavailable():
    result = policy().evaluate(
        make_quote(
            MONDAY
            + timedelta(
                seconds=1,
            )
        ),
        now=MONDAY,
    )

    assert (
        result.state
        is FxFreshness.FX_UNAVAILABLE
    )

    assert result.reason == "FUTURE_FX_TIMESTAMP"


def test_missing_provider_timestamp_is_unavailable():
    result = policy().evaluate(
        FxQuote(
            base_currency="USD",
            quote_currency="PLN",
            rate=3.75,
            provider="NBP",
            provider_timestamp=None,
            observed_at=MONDAY,
            source_quality=(
                FxSourceQuality.DAILY_REFERENCE
            ),
        ),
        now=MONDAY,
    )

    assert (
        result.state
        is FxFreshness.FX_UNAVAILABLE
    )

    assert (
        result.reason
        == "FX_TIMESTAMP_UNAVAILABLE"
    )


def test_threshold_must_not_exceed_96_hours():
    with pytest.raises(
        ValueError,
        match="must not exceed unavailable threshold",
    ):
        FxFreshnessPolicy(
            weekday_max_age_seconds=400000.0,
            weekend_max_age_seconds=7200.0,
        )
