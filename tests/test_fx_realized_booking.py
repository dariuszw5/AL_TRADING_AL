from dataclasses import FrozenInstanceError
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
    RealizedFxBookingError,
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


def booker():
    return RealizedFxBooker(
        clock=FixedClock(
            BOOKED_AT
        )
    )


def nbp_usd():
    return FxQuote(
        base_currency="USD",
        quote_currency="PLN",
        rate=3.7639,
        provider="NBP_TABLE_A",
        provider_timestamp=None,
        observed_at=BOOKED_AT,
        source_quality=(
            FxSourceQuality.DAILY_REFERENCE
        ),
        table="180/A/NBP/2026",
        effective_date=date(
            2026,
            9,
            16,
        ),
        labels=(
            "REFERENCE_ACCOUNTING_ONLY",
            "PUBLICATION_TIMESTAMP_UNAVAILABLE",
        ),
    )


def test_direct_nbp_usd_realized_booking_is_immutable():
    booking = booker().book(
        booking_id="rb-001",
        asset_id="AAPL",
        close_execution_id="exec-close-001",
        closed_at=CLOSED_AT,
        native_pnl=100.0,
        native_currency="USD",
        quotes=[
            nbp_usd(),
        ],
    )

    assert booking.booking_id == "rb-001"
    assert booking.native_pnl == 100.0
    assert booking.native_currency == "USD"

    assert booking.fx_pair == "USDPLN"
    assert booking.fx_path == "USD→PLN"
    assert booking.fx_rate == pytest.approx(
        3.7639
    )

    assert booking.pnl_pln == pytest.approx(
        376.39
    )

    assert booking.fx_provider == "NBP_TABLE_A"

    # No fake publication timestamp.
    assert booking.fx_timestamp is None

    assert booking.fx_table == "180/A/NBP/2026"

    assert booking.fx_effective_date == date(
        2026,
        9,
        16,
    )

    assert len(booking.fx_legs) == 1

    with pytest.raises(
        FrozenInstanceError
    ):
        booking.pnl_pln = 999.0


def test_nbp_booking_preserves_daily_reference_limitation():
    booking = booker().book(
        booking_id="rb-002",
        asset_id="AAPL",
        close_execution_id="exec-close-002",
        closed_at=CLOSED_AT,
        native_pnl=10.0,
        native_currency="USD",
        quotes=[
            nbp_usd(),
        ],
    )

    assert (
        "KNOWN_LIMITATION: "
        "DAILY_REFERENCE_INTRADAY_PUBLICATION_TIME_UNAVAILABLE"
        in booking.limitations
    )

    assert (
        "KNOWN_LIMITATION: "
        "FX_CONVERSION_COST_NOT_MODELLED"
        in booking.limitations
    )


def test_usdt_realized_booking_preserves_both_fx_legs():
    usdt_usd = FxQuote(
        base_currency="USDT",
        quote_currency="USD",
        rate=0.999165,
        provider="COINBASE_EXCHANGE",
        provider_timestamp=(
            CLOSED_AT
            - timedelta(
                seconds=1,
            )
        ),
        observed_at=CLOSED_AT,
        source_quality=(
            FxSourceQuality.LIVE
        ),
        bid=0.99916,
        ask=0.99917,
        labels=(
            "PUBLIC_ORDER_BOOK",
            "MIDPOINT_REFERENCE",
        ),
    )

    usd_pln = nbp_usd()

    booking = booker().book(
        booking_id="rb-003",
        asset_id="BTCUSDT",
        close_execution_id="exec-close-003",
        closed_at=CLOSED_AT,
        native_pnl=100.0,
        native_currency="USDT",
        quotes=[
            usdt_usd,
            usd_pln,
        ],
    )

    expected_rate = (
        0.999165
        * 3.7639
    )

    assert booking.fx_pair == "USDTPLN"
    assert booking.fx_path == "USDT→USD→PLN"

    assert booking.fx_rate == pytest.approx(
        expected_rate
    )

    assert booking.pnl_pln == pytest.approx(
        100.0
        * expected_rate
    )

    assert len(booking.fx_legs) == 2

    assert booking.fx_legs[0].pair == "USDTUSD"
    assert booking.fx_legs[0].bid == pytest.approx(
        0.99916
    )
    assert booking.fx_legs[0].ask == pytest.approx(
        0.99917
    )

    assert booking.fx_legs[1].pair == "USDPLN"
    assert booking.fx_legs[1].table == "180/A/NBP/2026"

    # Multi-leg path has no misleading synthetic
    # single top-level provider timestamp.
    assert booking.fx_timestamp is None

    assert booking.fx_provider == (
        "COINBASE_EXCHANGE|NBP_TABLE_A"
    )


def test_negative_native_pnl_remains_negative():
    booking = booker().book(
        booking_id="rb-004",
        asset_id="AAPL",
        close_execution_id="exec-close-004",
        closed_at=CLOSED_AT,
        native_pnl=-25.0,
        native_currency="USD",
        quotes=[
            nbp_usd(),
        ],
    )

    assert booking.pnl_pln == pytest.approx(
        -25.0
        * 3.7639
    )


def test_pln_native_booking_needs_no_fx():
    booking = booker().book(
        booking_id="rb-005",
        asset_id="PLN_TEST",
        close_execution_id="exec-close-005",
        closed_at=CLOSED_AT,
        native_pnl=123.45,
        native_currency="PLN",
        quotes=[],
    )

    assert booking.pnl_pln == 123.45
    assert booking.fx_pair == "PLNPLN"
    assert booking.fx_path == "PLN"
    assert booking.fx_rate == 1.0
    assert booking.fx_provider is None
    assert booking.fx_timestamp is None
    assert booking.fx_legs == ()
    assert booking.limitations == ()


def test_missing_usdt_usd_leg_fails_closed():
    with pytest.raises(
        RealizedFxBookingError,
        match="MISSING_FX_LEG:USDTUSD",
    ):
        booker().book(
            booking_id="rb-006",
            asset_id="BTCUSDT",
            close_execution_id="exec-close-006",
            closed_at=CLOSED_AT,
            native_pnl=100.0,
            native_currency="USDT",
            quotes=[
                nbp_usd(),
            ],
        )


def test_unsupported_currency_fails_closed():
    with pytest.raises(
        RealizedFxBookingError,
        match="NO_REALIZED_FX_PATH:JPY→PLN",
    ):
        booker().book(
            booking_id="rb-007",
            asset_id="JPY_TEST",
            close_execution_id="exec-close-007",
            closed_at=CLOSED_AT,
            native_pnl=100.0,
            native_currency="JPY",
            quotes=[],
        )


def test_live_quote_after_close_is_future_data():
    quote = FxQuote(
        base_currency="USD",
        quote_currency="PLN",
        rate=3.8,
        provider="LIVE_TEST",
        provider_timestamp=(
            CLOSED_AT
            + timedelta(
                seconds=1,
            )
        ),
        observed_at=BOOKED_AT,
        source_quality=(
            FxSourceQuality.LIVE
        ),
    )

    with pytest.raises(
        RealizedFxBookingError,
        match="FX_TIMESTAMP_AFTER_CLOSE:USDPLN",
    ):
        booker().book(
            booking_id="rb-008",
            asset_id="AAPL",
            close_execution_id="exec-close-008",
            closed_at=CLOSED_AT,
            native_pnl=10.0,
            native_currency="USD",
            quotes=[
                quote,
            ],
        )


def test_daily_reference_future_effective_date_is_rejected():
    quote = FxQuote(
        base_currency="USD",
        quote_currency="PLN",
        rate=3.8,
        provider="NBP_TABLE_A",
        provider_timestamp=None,
        observed_at=BOOKED_AT,
        source_quality=(
            FxSourceQuality.DAILY_REFERENCE
        ),
        table="181/A/NBP/2026",
        effective_date=date(
            2026,
            9,
            17,
        ),
    )

    with pytest.raises(
        RealizedFxBookingError,
        match="FX_EFFECTIVE_DATE_AFTER_CLOSE:USDPLN",
    ):
        booker().book(
            booking_id="rb-009",
            asset_id="AAPL",
            close_execution_id="exec-close-009",
            closed_at=CLOSED_AT,
            native_pnl=10.0,
            native_currency="USD",
            quotes=[
                quote,
            ],
        )


def test_daily_reference_requires_table_and_effective_date():
    quote = FxQuote(
        base_currency="USD",
        quote_currency="PLN",
        rate=3.8,
        provider="DAILY_TEST",
        provider_timestamp=None,
        observed_at=BOOKED_AT,
        source_quality=(
            FxSourceQuality.DAILY_REFERENCE
        ),
    )

    with pytest.raises(
        RealizedFxBookingError,
        match="DAILY_REFERENCE_METADATA_INCOMPLETE:USDPLN",
    ):
        booker().book(
            booking_id="rb-010",
            asset_id="AAPL",
            close_execution_id="exec-close-010",
            closed_at=CLOSED_AT,
            native_pnl=10.0,
            native_currency="USD",
            quotes=[
                quote,
            ],
        )


def test_non_daily_reference_requires_provider_timestamp():
    quote = FxQuote(
        base_currency="USD",
        quote_currency="PLN",
        rate=3.8,
        provider="LIVE_TEST",
        provider_timestamp=None,
        observed_at=BOOKED_AT,
        source_quality=(
            FxSourceQuality.LIVE
        ),
    )

    with pytest.raises(
        RealizedFxBookingError,
        match="FX_TIMESTAMP_REQUIRED:USDPLN",
    ):
        booker().book(
            booking_id="rb-011",
            asset_id="AAPL",
            close_execution_id="exec-close-011",
            closed_at=CLOSED_AT,
            native_pnl=10.0,
            native_currency="USD",
            quotes=[
                quote,
            ],
        )


def test_booked_at_cannot_precede_trade_close():
    early_clock = FixedClock(
        CLOSED_AT
        - timedelta(
            seconds=1,
        )
    )

    early_booker = RealizedFxBooker(
        clock=early_clock
    )

    with pytest.raises(
        RealizedFxBookingError,
        match="BOOKING_BEFORE_CLOSE",
    ):
        early_booker.book(
            booking_id="rb-012",
            asset_id="AAPL",
            close_execution_id="exec-close-012",
            closed_at=CLOSED_AT,
            native_pnl=10.0,
            native_currency="USD",
            quotes=[
                nbp_usd(),
            ],
        )


def test_duplicate_pair_is_rejected():
    first = nbp_usd()

    second = FxQuote(
        base_currency="USD",
        quote_currency="PLN",
        rate=3.8,
        provider="OTHER",
        provider_timestamp=(
            CLOSED_AT
            - timedelta(
                seconds=10,
            )
        ),
        observed_at=CLOSED_AT,
        source_quality=(
            FxSourceQuality.LIVE
        ),
    )

    with pytest.raises(
        RealizedFxBookingError,
        match="DUPLICATE_FX_LEG:USDPLN",
    ):
        booker().book(
            booking_id="rb-013",
            asset_id="AAPL",
            close_execution_id="exec-close-013",
            closed_at=CLOSED_AT,
            native_pnl=10.0,
            native_currency="USD",
            quotes=[
                first,
                second,
            ],
        )


def test_required_identifiers_cannot_be_blank():
    with pytest.raises(
        RealizedFxBookingError,
        match="booking_id is required",
    ):
        booker().book(
            booking_id="",
            asset_id="AAPL",
            close_execution_id="exec-close-014",
            closed_at=CLOSED_AT,
            native_pnl=10.0,
            native_currency="USD",
            quotes=[
                nbp_usd(),
            ],
        )
