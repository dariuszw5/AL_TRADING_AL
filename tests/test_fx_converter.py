from datetime import (
    datetime,
    timedelta,
    timezone,
)

import pytest

from src.core.clock import FixedClock
from src.fx.converter import (
    CurrencyConverter,
)
from src.fx.freshness import (
    FxFreshnessPolicy,
)
from src.fx.models import (
    FxFreshness,
    FxQuote,
    FxSourceQuality,
)


NOW = datetime(
    2026,
    9,
    16,
    17,
    0,
    tzinfo=timezone.utc,
)


def policy():
    return FxFreshnessPolicy(
        weekday_max_age_seconds=900.0,
        weekend_max_age_seconds=7200.0,
    )


def make_quote(
    base,
    quote,
    rate,
    *,
    age_seconds=0,
    provider="TEST",
    source_quality=FxSourceQuality.LIVE,
    bid=None,
    ask=None,
):
    return FxQuote(
        base_currency=base,
        quote_currency=quote,
        rate=rate,
        provider=provider,
        provider_timestamp=(
            NOW
            - timedelta(
                seconds=age_seconds,
            )
        ),
        observed_at=NOW,
        source_quality=source_quality,
        bid=bid,
        ask=ask,
    )


def converter():
    return CurrencyConverter(
        clock=FixedClock(NOW),
        freshness_policy=policy(),
    )


def test_usd_to_pln_direct_conversion():
    usd_pln = make_quote(
        "USD",
        "PLN",
        3.7639,
        provider="YAHOO_FINANCE",
        source_quality=(
            FxSourceQuality.STALE_PRONE
        ),
    )

    result = converter().convert_to_pln(
        100.0,
        "USD",
        [usd_pln],
    )

    assert result.converted_amount == pytest.approx(
        376.39
    )

    assert result.fx_path.text == "USD→PLN"

    assert (
        result.freshness
        is FxFreshness.FX_FRESH
    )

    # Freshness does not upgrade source quality.
    assert (
        result.legs[0].source_quality
        is FxSourceQuality.STALE_PRONE
    )


def test_eur_to_pln_direct_conversion():
    eur_pln = make_quote(
        "EUR",
        "PLN",
        4.3435,
    )

    result = converter().convert_to_pln(
        10.0,
        "EUR",
        [eur_pln],
    )

    assert result.converted_amount == pytest.approx(
        43.435
    )

    assert result.fx_path.text == "EUR→PLN"


def test_usdt_to_pln_uses_two_real_legs():
    usdt_usd = make_quote(
        "USDT",
        "USD",
        0.999165,
        provider="COINBASE_EXCHANGE",
        bid=0.99916,
        ask=0.99917,
    )

    usd_pln = make_quote(
        "USD",
        "PLN",
        3.7771,
        provider="YAHOO_FINANCE",
        source_quality=(
            FxSourceQuality.STALE_PRONE
        ),
    )

    result = converter().convert_to_pln(
        100.0,
        "USDT",
        [
            usdt_usd,
            usd_pln,
        ],
    )

    assert result.fx_path.text == "USDT→USD→PLN"

    assert result.converted_amount == pytest.approx(
        100.0
        * 0.999165
        * 3.7771
    )

    assert result.legs == (
        usdt_usd,
        usd_pln,
    )

    assert result.limitations == (
        "KNOWN_LIMITATION: "
        "FX_CONVERSION_COST_NOT_MODELLED",
    )


def test_usdt_missing_depeg_leg_fails_closed():
    usd_pln = make_quote(
        "USD",
        "PLN",
        3.7771,
    )

    result = converter().convert_to_pln(
        100.0,
        "USDT",
        [usd_pln],
    )

    assert result.converted_amount is None

    assert (
        result.freshness
        is FxFreshness.FX_UNAVAILABLE
    )

    assert (
        result.unavailable_reason
        == "MISSING_FX_LEG:USDTUSD"
    )


def test_usdt_never_silently_uses_one_to_one():
    usdt_usd = make_quote(
        "USDT",
        "USD",
        0.95,
    )

    usd_pln = make_quote(
        "USD",
        "PLN",
        4.0,
    )

    result = converter().convert_to_pln(
        10.0,
        "USDT",
        [
            usdt_usd,
            usd_pln,
        ],
    )

    assert result.converted_amount == pytest.approx(
        38.0
    )

    assert result.converted_amount != 40.0


def test_stale_leg_makes_entire_path_stale():
    usdt_usd = make_quote(
        "USDT",
        "USD",
        1.0,
        age_seconds=1000,
    )

    usd_pln = make_quote(
        "USD",
        "PLN",
        4.0,
    )

    result = converter().convert_to_pln(
        10.0,
        "USDT",
        [
            usdt_usd,
            usd_pln,
        ],
    )

    assert result.freshness is FxFreshness.FX_STALE
    assert result.quote_age_seconds == 1000.0


def test_expired_leg_makes_entire_path_unavailable():
    usdt_usd = make_quote(
        "USDT",
        "USD",
        1.0,
        age_seconds=(
            96 * 60 * 60
            + 1
        ),
    )

    usd_pln = make_quote(
        "USD",
        "PLN",
        4.0,
    )

    result = converter().convert_to_pln(
        10.0,
        "USDT",
        [
            usdt_usd,
            usd_pln,
        ],
    )

    assert result.converted_amount is None

    assert (
        result.freshness
        is FxFreshness.FX_UNAVAILABLE
    )


def test_future_quote_is_never_used():
    future = FxQuote(
        base_currency="USD",
        quote_currency="PLN",
        rate=999.0,
        provider="BAD",
        provider_timestamp=(
            NOW
            + timedelta(
                seconds=1,
            )
        ),
        observed_at=NOW,
        source_quality=(
            FxSourceQuality.LIVE
        ),
    )

    result = converter().convert_to_pln(
        10.0,
        "USD",
        [future],
    )

    assert result.converted_amount is None

    assert (
        result.unavailable_reason
        == "FUTURE_FX_TIMESTAMP"
    )


def test_pln_identity_is_not_an_fx_assumption():
    result = converter().convert_to_pln(
        123.45,
        "PLN",
        [],
    )

    assert result.converted_amount == 123.45
    assert result.fx_path.text == "PLN"
    assert result.legs == ()

    assert (
        result.freshness
        is FxFreshness.FX_FRESH
    )


def test_unsupported_currency_fails_closed():
    result = converter().convert_to_pln(
        100.0,
        "JPY",
        [],
    )

    assert result.converted_amount is None

    assert (
        result.unavailable_reason
        == "NO_FX_PATH:JPY→PLN"
    )


def test_duplicate_pair_is_rejected():
    first = make_quote(
        "USD",
        "PLN",
        3.7,
    )

    second = make_quote(
        "USD",
        "PLN",
        3.8,
    )

    with pytest.raises(
        ValueError,
        match="duplicate FX quote",
    ):
        converter().convert_to_pln(
            10.0,
            "USD",
            [
                first,
                second,
            ],
        )
