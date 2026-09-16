from datetime import (
    date,
    datetime,
    timedelta,
    timezone,
)

import pytest

from src.core.clock import FixedClock
from src.fx.models import (
    FxQuote,
    FxSourceQuality,
)
from src.fx.realized_booking import (
    RealizedFxBooker,
)
from src.fx.realized_selection import (
    RealizedFxSelectionError,
    RealizedFxSelectionPolicy,
)


CLOSED_AT = datetime(
    2026,
    9,
    16,
    17,
    0,
    tzinfo=timezone.utc,
)

BOOKED_AT = datetime(
    2026,
    9,
    16,
    18,
    0,
    tzinfo=timezone.utc,
)


def policy():
    # TEST-ONLY thresholds.
    # Production values are NOT frozen in A.6.
    return RealizedFxSelectionPolicy(
        market_max_age_seconds=30.0,
        daily_reference_max_age_days=7,
    )


def nbp(
    currency,
    rate,
    effective_date,
    table,
    observed_at=BOOKED_AT,
):
    return FxQuote(
        base_currency=currency,
        quote_currency="PLN",
        rate=rate,
        provider="NBP_TABLE_A",
        provider_timestamp=None,
        observed_at=observed_at,
        source_quality=(
            FxSourceQuality.DAILY_REFERENCE
        ),
        table=table,
        effective_date=effective_date,
        labels=(
            "REFERENCE_ACCOUNTING_ONLY",
            "PUBLICATION_TIMESTAMP_UNAVAILABLE",
        ),
    )


def coinbase(
    rate,
    provider_timestamp,
):
    return FxQuote(
        base_currency="USDT",
        quote_currency="USD",
        rate=rate,
        provider="COINBASE_EXCHANGE",
        provider_timestamp=provider_timestamp,
        observed_at=BOOKED_AT,
        source_quality=(
            FxSourceQuality.LIVE
        ),
        bid=rate - 0.000005,
        ask=rate + 0.000005,
        labels=(
            "PUBLIC_ORDER_BOOK",
            "MIDPOINT_REFERENCE",
        ),
    )


def test_same_day_nbp_observed_before_close_is_eligible():
    prior = nbp(
        "USD",
        3.70,
        date(2026, 9, 15),
        "179/A/NBP/2026",
    )

    same_day_known = nbp(
        "USD",
        3.7639,
        date(2026, 9, 16),
        "180/A/NBP/2026",
        observed_at=(
            CLOSED_AT
            - timedelta(minutes=10)
        ),
    )

    selected = policy().select(
        closed_at=CLOSED_AT,
        native_currency="USD",
        quotes=[
            prior,
            same_day_known,
        ],
    )

    assert selected == (
        same_day_known,
    )


def test_same_day_nbp_observed_after_close_is_not_backfilled():
    same_day_late = nbp(
        "USD",
        3.7639,
        date(2026, 9, 16),
        "180/A/NBP/2026",
        observed_at=BOOKED_AT,
    )

    with pytest.raises(
        RealizedFxSelectionError,
        match="SAFE_NBP_REFERENCE_UNAVAILABLE_AT_CLOSE:USDPLN",
    ):
        policy().select(
            closed_at=CLOSED_AT,
            native_currency="USD",
            quotes=[
                same_day_late,
            ],
        )


def test_prior_day_nbp_is_safe_when_same_day_was_seen_after_close():
    prior = nbp(
        "USD",
        3.70,
        date(2026, 9, 15),
        "179/A/NBP/2026",
    )

    same_day_late = nbp(
        "USD",
        3.7639,
        date(2026, 9, 16),
        "180/A/NBP/2026",
        observed_at=BOOKED_AT,
    )

    selected = policy().select(
        closed_at=CLOSED_AT,
        native_currency="USD",
        quotes=[
            prior,
            same_day_late,
        ],
    )

    assert selected == (
        prior,
    )


def test_latest_prior_nbp_reference_is_selected():
    old = nbp(
        "USD",
        3.60,
        date(2026, 9, 14),
        "178/A/NBP/2026",
    )

    latest = nbp(
        "USD",
        3.70,
        date(2026, 9, 15),
        "179/A/NBP/2026",
    )

    selected = policy().select(
        closed_at=CLOSED_AT,
        native_currency="USD",
        quotes=[
            old,
            latest,
        ],
    )

    assert selected == (
        latest,
    )


def test_weekend_or_holiday_gap_can_use_prior_reference():
    monday_close = datetime(
        2026,
        9,
        21,
        10,
        0,
        tzinfo=timezone.utc,
    )

    friday = nbp(
        "USD",
        3.72,
        date(2026, 9, 18),
        "182/A/NBP/2026",
    )

    monday_late = nbp(
        "USD",
        3.74,
        date(2026, 9, 21),
        "183/A/NBP/2026",
        observed_at=(
            monday_close
            + timedelta(hours=2)
        ),
    )

    selected = policy().select(
        closed_at=monday_close,
        native_currency="USD",
        quotes=[
            friday,
            monday_late,
        ],
    )

    assert selected == (
        friday,
    )


def test_daily_reference_too_old_fails_closed():
    too_old = nbp(
        "USD",
        3.60,
        date(2026, 9, 8),
        "174/A/NBP/2026",
    )

    with pytest.raises(
        RealizedFxSelectionError,
        match="DAILY_REFERENCE_TOO_OLD:USDPLN",
    ):
        policy().select(
            closed_at=CLOSED_AT,
            native_currency="USD",
            quotes=[
                too_old,
            ],
        )


def test_future_effective_date_is_never_selected():
    future = nbp(
        "USD",
        3.90,
        date(2026, 9, 17),
        "181/A/NBP/2026",
        observed_at=(
            CLOSED_AT
            - timedelta(minutes=1)
        ),
    )

    with pytest.raises(
        RealizedFxSelectionError,
        match="SAFE_NBP_REFERENCE_UNAVAILABLE_AT_CLOSE:USDPLN",
    ):
        policy().select(
            closed_at=CLOSED_AT,
            native_currency="USD",
            quotes=[
                future,
            ],
        )


def test_ambiguous_same_effective_date_fails_closed():
    first = nbp(
        "USD",
        3.70,
        date(2026, 9, 15),
        "179/A/NBP/2026",
    )

    second = nbp(
        "USD",
        3.71,
        date(2026, 9, 15),
        "179/A/NBP/2026-DUP",
    )

    with pytest.raises(
        RealizedFxSelectionError,
        match="AMBIGUOUS_DAILY_REFERENCE:USDPLN",
    ):
        policy().select(
            closed_at=CLOSED_AT,
            native_currency="USD",
            quotes=[
                first,
                second,
            ],
        )


def test_eur_uses_nbp_daily_reference():
    previous = nbp(
        "EUR",
        4.30,
        date(2026, 9, 15),
        "179/A/NBP/2026",
    )

    selected = policy().select(
        closed_at=CLOSED_AT,
        native_currency="EUR",
        quotes=[
            previous,
        ],
    )

    assert selected == (
        previous,
    )


def test_usdt_selects_latest_coinbase_quote_not_after_close():
    old = coinbase(
        0.9990,
        CLOSED_AT - timedelta(seconds=10),
    )

    latest = coinbase(
        0.9992,
        CLOSED_AT - timedelta(seconds=1),
    )

    future = coinbase(
        1.0001,
        CLOSED_AT + timedelta(seconds=1),
    )

    usd_pln = nbp(
        "USD",
        3.70,
        date(2026, 9, 15),
        "179/A/NBP/2026",
    )

    selected = policy().select(
        closed_at=CLOSED_AT,
        native_currency="USDT",
        quotes=[
            old,
            future,
            usd_pln,
            latest,
        ],
    )

    assert selected == (
        latest,
        usd_pln,
    )


def test_usdt_market_quote_exact_max_age_is_allowed():
    exact = coinbase(
        0.9992,
        CLOSED_AT - timedelta(seconds=30),
    )

    usd_pln = nbp(
        "USD",
        3.70,
        date(2026, 9, 15),
        "179/A/NBP/2026",
    )

    selected = policy().select(
        closed_at=CLOSED_AT,
        native_currency="USDT",
        quotes=[
            exact,
            usd_pln,
        ],
    )

    assert selected[0] == exact


def test_usdt_market_quote_older_than_limit_fails_closed():
    stale = coinbase(
        0.9992,
        CLOSED_AT - timedelta(seconds=31),
    )

    usd_pln = nbp(
        "USD",
        3.70,
        date(2026, 9, 15),
        "179/A/NBP/2026",
    )

    with pytest.raises(
        RealizedFxSelectionError,
        match="MARKET_FX_QUOTE_TOO_OLD:USDTUSD",
    ):
        policy().select(
            closed_at=CLOSED_AT,
            native_currency="USDT",
            quotes=[
                stale,
                usd_pln,
            ],
        )


def test_future_coinbase_quote_is_not_used():
    future = coinbase(
        1.0,
        CLOSED_AT + timedelta(seconds=1),
    )

    usd_pln = nbp(
        "USD",
        3.70,
        date(2026, 9, 15),
        "179/A/NBP/2026",
    )

    with pytest.raises(
        RealizedFxSelectionError,
        match="MARKET_FX_QUOTE_UNAVAILABLE_AT_CLOSE:USDTUSD",
    ):
        policy().select(
            closed_at=CLOSED_AT,
            native_currency="USDT",
            quotes=[
                future,
                usd_pln,
            ],
        )


def test_pln_requires_no_fx_selection():
    assert policy().select(
        closed_at=CLOSED_AT,
        native_currency="PLN",
        quotes=[],
    ) == ()


def test_unsupported_currency_fails_closed():
    with pytest.raises(
        RealizedFxSelectionError,
        match="NO_REALIZED_FX_PATH:JPY→PLN",
    ):
        policy().select(
            closed_at=CLOSED_AT,
            native_currency="JPY",
            quotes=[],
        )


def test_selection_integrates_with_immutable_booking():
    usdt_usd = coinbase(
        0.9992,
        CLOSED_AT - timedelta(seconds=1),
    )

    usd_pln = nbp(
        "USD",
        3.70,
        date(2026, 9, 15),
        "179/A/NBP/2026",
    )

    selected = policy().select(
        closed_at=CLOSED_AT,
        native_currency="USDT",
        quotes=[
            usdt_usd,
            usd_pln,
        ],
    )

    booking = RealizedFxBooker(
        clock=FixedClock(
            BOOKED_AT
        )
    ).book(
        booking_id="selection-booking-001",
        asset_id="BTCUSDT",
        close_execution_id="exec-close-selection-001",
        closed_at=CLOSED_AT,
        native_pnl=100.0,
        native_currency="USDT",
        quotes=selected,
    )

    assert booking.fx_path == "USDT→USD→PLN"

    assert booking.fx_rate == pytest.approx(
        0.9992 * 3.70
    )

    assert booking.pnl_pln == pytest.approx(
        100.0 * 0.9992 * 3.70
    )

    assert booking.fx_effective_date == date(
        2026,
        9,
        15,
    )


def test_selection_policy_thresholds_must_be_positive():
    with pytest.raises(
        ValueError,
        match="market_max_age_seconds must be positive",
    ):
        RealizedFxSelectionPolicy(
            market_max_age_seconds=0,
            daily_reference_max_age_days=7,
        )

    with pytest.raises(
        ValueError,
        match="daily_reference_max_age_days must be positive",
    ):
        RealizedFxSelectionPolicy(
            market_max_age_seconds=30,
            daily_reference_max_age_days=0,
        )
