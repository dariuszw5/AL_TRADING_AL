from datetime import datetime, timezone

import pytest

from src.market.market_session import (
    MarketSessionService,
    SessionQuality,
    SessionState,
)


UTC = timezone.utc


def utc(
    year,
    month,
    day,
    hour,
    minute=0,
):
    return datetime(
        year,
        month,
        day,
        hour,
        minute,
        tzinfo=UTC,
    )


@pytest.fixture
def service():
    return MarketSessionService()


def test_naive_datetime_is_rejected(service):
    with pytest.raises(
        ValueError,
        match="timezone-aware",
    ):
        service.get_session(
            "BTCUSDT",
            datetime(
                2026,
                9,
                16,
                12,
                0,
            ),
        )


def test_crypto_is_open_on_weekend(service):
    result = service.get_session(
        "BTCUSDT",
        utc(
            2026,
            9,
            19,
            12,
        ),
    )

    assert result.state is SessionState.OPEN
    assert result.is_open is True
    assert (
        result.session_quality
        is SessionQuality.EXCHANGE_CALENDAR
    )


def test_aapl_pre_market(service):
    result = service.get_session(
        "AAPL",
        utc(
            2026,
            9,
            16,
            12,
        ),
    )

    assert (
        result.state
        is SessionState.PRE_MARKET
    )


def test_aapl_regular(service):
    result = service.get_session(
        "AAPL",
        utc(
            2026,
            9,
            16,
            15,
        ),
    )

    assert (
        result.state
        is SessionState.REGULAR
    )

    assert (
        result.session_quality
        is SessionQuality.EXCHANGE_CALENDAR
    )


def test_aapl_after_hours(service):
    result = service.get_session(
        "AAPL",
        utc(
            2026,
            9,
            16,
            21,
        ),
    )

    assert (
        result.state
        is SessionState.AFTER_HOURS
    )


def test_aapl_weekend_closed(service):
    result = service.get_session(
        "AAPL",
        utc(
            2026,
            9,
            19,
            15,
        ),
    )

    assert (
        result.state
        is SessionState.CLOSED
    )


def test_aapl_thanksgiving_closed(service):
    result = service.get_session(
        "AAPL",
        utc(
            2026,
            11,
            26,
            15,
        ),
    )

    assert (
        result.state
        is SessionState.CLOSED
    )

    assert (
        result.reason
        == "EXCHANGE_HOLIDAY"
    )


def test_aapl_2025_special_closure(service):
    result = service.get_session(
        "AAPL",
        utc(
            2025,
            1,
            9,
            15,
        ),
    )

    assert (
        result.state
        is SessionState.CLOSED
    )


def test_aapl_early_close_regular_before_1pm(service):
    result = service.get_session(
        "AAPL",
        utc(
            2026,
            11,
            27,
            17,
            59,
        ),
    )

    assert (
        result.state
        is SessionState.REGULAR
    )

    assert (
        result.reason
        == "EARLY_CLOSE_REGULAR"
    )


def test_aapl_early_close_after_1pm_is_unknown(
    service,
):
    result = service.get_session(
        "AAPL",
        utc(
            2026,
            11,
            27,
            18,
            1,
        ),
    )

    assert (
        result.state
        is SessionState.UNKNOWN
    )

    assert (
        result.session_quality
        is SessionQuality.UNKNOWN
    )


def test_aapl_december_24_early_close(service):
    before = service.get_session(
        "AAPL",
        utc(
            2026,
            12,
            24,
            17,
            59,
        ),
    )

    after = service.get_session(
        "AAPL",
        utc(
            2026,
            12,
            24,
            18,
            1,
        ),
    )

    assert (
        before.state
        is SessionState.REGULAR
    )

    assert (
        after.state
        is SessionState.UNKNOWN
    )


def test_aapl_dst_before_spring_change(service):
    result = service.get_session(
        "AAPL",
        utc(
            2026,
            3,
            6,
            14,
            30,
        ),
    )

    assert (
        result.state
        is SessionState.REGULAR
    )

    assert result.local_time.hour == 9
    assert result.local_time.minute == 30


def test_aapl_dst_after_spring_change(service):
    result = service.get_session(
        "AAPL",
        utc(
            2026,
            3,
            9,
            13,
            30,
        ),
    )

    assert (
        result.state
        is SessionState.REGULAR
    )

    assert result.local_time.hour == 9
    assert result.local_time.minute == 30


def test_aapl_calendar_expiry_fails_closed(
    service,
):
    result = service.get_session(
        "AAPL",
        utc(
            2027,
            6,
            15,
            15,
        ),
    )

    assert (
        result.state
        is SessionState.UNKNOWN
    )

    assert (
        result.session_quality
        is SessionQuality.UNKNOWN
    )

    assert (
        result.reason
        == "CALENDAR_OUT_OF_COVERAGE"
    )


def test_fx_sunday_spring_dst_transition(
    service,
):
    before = service.get_session(
        "EURUSD",
        utc(
            2026,
            3,
            8,
            20,
            59,
        ),
    )

    after = service.get_session(
        "EURUSD",
        utc(
            2026,
            3,
            8,
            21,
            0,
        ),
    )

    assert (
        before.state
        is SessionState.CLOSED
    )

    assert (
        after.state
        is SessionState.OPEN
    )


def test_fx_sunday_autumn_dst_transition(
    service,
):
    before = service.get_session(
        "EURUSD",
        utc(
            2026,
            11,
            1,
            21,
            59,
        ),
    )

    after = service.get_session(
        "EURUSD",
        utc(
            2026,
            11,
            1,
            22,
            0,
        ),
    )

    assert (
        before.state
        is SessionState.CLOSED
    )

    assert (
        after.state
        is SessionState.OPEN
    )


def test_fx_friday_close(service):
    before = service.get_session(
        "EURUSD",
        utc(
            2026,
            9,
            18,
            20,
            59,
        ),
    )

    after = service.get_session(
        "EURUSD",
        utc(
            2026,
            9,
            18,
            21,
            0,
        ),
    )

    assert (
        before.state
        is SessionState.OPEN
    )

    assert (
        after.state
        is SessionState.CLOSED
    )


def test_fx_christmas_closed(service):
    result = service.get_session(
        "EURUSD",
        utc(
            2026,
            12,
            25,
            15,
        ),
    )

    assert (
        result.state
        is SessionState.CLOSED
    )


def test_fx_quality_is_approximated(service):
    result = service.get_session(
        "EURUSD",
        utc(
            2026,
            9,
            16,
            15,
        ),
    )

    assert (
        result.session_quality
        is SessionQuality.APPROXIMATED
    )


@pytest.mark.parametrize(
    "asset_id",
    [
        "GOLD_FUT_CONT",
        "WTI_FUT_CONT",
    ],
)
def test_cme_proxy_normal_session_open(
    service,
    asset_id,
):
    result = service.get_session(
        asset_id,
        utc(
            2026,
            9,
            16,
            15,
        ),
    )

    assert (
        result.state
        is SessionState.OPEN
    )

    assert (
        result.session_quality
        is SessionQuality.APPROXIMATED
    )


@pytest.mark.parametrize(
    "asset_id",
    [
        "GOLD_FUT_CONT",
        "WTI_FUT_CONT",
    ],
)
def test_cme_proxy_daily_maintenance(
    service,
    asset_id,
):
    result = service.get_session(
        asset_id,
        utc(
            2026,
            9,
            16,
            21,
            30,
        ),
    )

    assert (
        result.state
        is SessionState.MAINTENANCE
    )


def test_cme_proxy_sunday_reopen(service):
    before = service.get_session(
        "GOLD_FUT_CONT",
        utc(
            2026,
            9,
            20,
            21,
            59,
        ),
    )

    after = service.get_session(
        "GOLD_FUT_CONT",
        utc(
            2026,
            9,
            20,
            22,
            0,
        ),
    )

    assert (
        before.state
        is SessionState.CLOSED
    )

    assert (
        after.state
        is SessionState.OPEN
    )


def test_cme_special_holiday_schedule_is_unknown(
    service,
):
    result = service.get_session(
        "GOLD_FUT_CONT",
        utc(
            2026,
            11,
            26,
            15,
        ),
    )

    assert (
        result.state
        is SessionState.UNKNOWN
    )

    assert (
        result.session_quality
        is SessionQuality.UNKNOWN
    )

    assert (
        result.reason
        == (
            "CME_SPECIAL_HOURS_"
            "NOT_PRODUCT_VERIFIED"
        )
    )


def test_cme_calendar_outside_coverage_unknown(
    service,
):
    result = service.get_session(
        "WTI_FUT_CONT",
        utc(
            2025,
            9,
            16,
            15,
        ),
    )

    assert (
        result.state
        is SessionState.UNKNOWN
    )

    assert (
        result.reason
        == "CME_CALENDAR_OUT_OF_COVERAGE"
    )


def test_observed_at_is_normalized_to_utc(
    service,
):
    result = service.get_session(
        "BTCUSDT",
        datetime.fromisoformat(
            "2026-09-16T17:00:00+02:00"
        ),
    )

    assert (
        result.observed_at.tzinfo
        is timezone.utc
    )

    assert (
        result.observed_at.hour
        == 15
    )

def test_new_york_dst_boundary_is_deterministic(
    service,
):
    before = service._us_local_time(
        utc(
            2026,
            3,
            8,
            6,
            59,
        ),
        "America/New_York",
    )

    after = service._us_local_time(
        utc(
            2026,
            3,
            8,
            7,
            0,
        ),
        "America/New_York",
    )

    assert before.utcoffset().total_seconds() == -5 * 3600
    assert after.utcoffset().total_seconds() == -4 * 3600

    assert before.hour == 1
    assert before.minute == 59

    assert after.hour == 3
    assert after.minute == 0


def test_chicago_dst_boundary_is_deterministic(
    service,
):
    before = service._us_local_time(
        utc(
            2026,
            3,
            8,
            7,
            59,
        ),
        "America/Chicago",
    )

    after = service._us_local_time(
        utc(
            2026,
            3,
            8,
            8,
            0,
        ),
        "America/Chicago",
    )

    assert before.utcoffset().total_seconds() == -6 * 3600
    assert after.utcoffset().total_seconds() == -5 * 3600

    assert before.hour == 1
    assert before.minute == 59

    assert after.hour == 3
    assert after.minute == 0


def test_new_york_autumn_dst_boundary(
    service,
):
    before = service._us_local_time(
        utc(
            2026,
            11,
            1,
            5,
            59,
        ),
        "America/New_York",
    )

    after = service._us_local_time(
        utc(
            2026,
            11,
            1,
            6,
            0,
        ),
        "America/New_York",
    )

    assert before.utcoffset().total_seconds() == -4 * 3600
    assert after.utcoffset().total_seconds() == -5 * 3600

    assert before.hour == 1
    assert after.hour == 1
