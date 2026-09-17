from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from src.fx.freshness import (
    PRODUCTION_WEEKDAY_MAX_FX_AGE_SECONDS,
    PRODUCTION_WEEKEND_MAX_FX_AGE_SECONDS,
    UNAVAILABLE_AFTER_SECONDS,
    production_fx_freshness_policy,
)
from src.fx.models import FxFreshness


UTC = timezone.utc

MONDAY = datetime(
    2026,
    9,
    14,
    12,
    0,
    tzinfo=UTC,
)

SATURDAY = datetime(
    2026,
    9,
    19,
    12,
    0,
    tzinfo=UTC,
)


def quote_at(timestamp):
    return SimpleNamespace(
        provider_timestamp=timestamp,
    )


def test_production_thresholds_are_frozen_at_two_hours():
    assert (
        PRODUCTION_WEEKDAY_MAX_FX_AGE_SECONDS
        == 2 * 60 * 60
    )

    assert (
        PRODUCTION_WEEKEND_MAX_FX_AGE_SECONDS
        == 2 * 60 * 60
    )


def test_weekday_and_weekend_are_separately_configured_fields():
    policy = production_fx_freshness_policy()

    assert (
        policy.weekday_max_age_seconds
        == PRODUCTION_WEEKDAY_MAX_FX_AGE_SECONDS
    )

    assert (
        policy.weekend_max_age_seconds
        == PRODUCTION_WEEKEND_MAX_FX_AGE_SECONDS
    )


def test_weekday_just_under_two_hours_is_fresh():
    policy = production_fx_freshness_policy()

    result = policy.evaluate(
        quote_at(
            MONDAY
            - timedelta(
                seconds=(
                    PRODUCTION_WEEKDAY_MAX_FX_AGE_SECONDS
                    - 1
                )
            )
        ),
        now=MONDAY,
    )

    assert result.state is FxFreshness.FX_FRESH


def test_weekday_exactly_two_hours_is_stale():
    policy = production_fx_freshness_policy()

    result = policy.evaluate(
        quote_at(
            MONDAY
            - timedelta(
                seconds=(
                    PRODUCTION_WEEKDAY_MAX_FX_AGE_SECONDS
                )
            )
        ),
        now=MONDAY,
    )

    assert result.state is FxFreshness.FX_STALE


def test_weekend_exactly_two_hours_is_stale():
    policy = production_fx_freshness_policy()

    result = policy.evaluate(
        quote_at(
            SATURDAY
            - timedelta(
                seconds=(
                    PRODUCTION_WEEKEND_MAX_FX_AGE_SECONDS
                )
            )
        ),
        now=SATURDAY,
    )

    assert result.state is FxFreshness.FX_STALE


def test_exactly_96_hours_remains_stale():
    policy = production_fx_freshness_policy()

    result = policy.evaluate(
        quote_at(
            SATURDAY
            - timedelta(
                seconds=UNAVAILABLE_AFTER_SECONDS
            )
        ),
        now=SATURDAY,
    )

    assert result.state is FxFreshness.FX_STALE


def test_more_than_96_hours_is_unavailable():
    policy = production_fx_freshness_policy()

    result = policy.evaluate(
        quote_at(
            SATURDAY
            - timedelta(
                seconds=(
                    UNAVAILABLE_AFTER_SECONDS
                    + 1
                )
            )
        ),
        now=SATURDAY,
    )

    assert result.state is FxFreshness.FX_UNAVAILABLE
    assert result.reason == "FX_QUOTE_EXPIRED"


def test_future_provider_timestamp_remains_fail_closed():
    policy = production_fx_freshness_policy()

    result = policy.evaluate(
        quote_at(
            MONDAY
            + timedelta(seconds=1)
        ),
        now=MONDAY,
    )

    assert result.state is FxFreshness.FX_UNAVAILABLE
    assert result.reason == "FUTURE_FX_TIMESTAMP"