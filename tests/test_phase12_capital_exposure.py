from datetime import (
    datetime,
    timedelta,
    timezone,
)
from decimal import Decimal

import pytest

from src.core.clock import FixedClock
from src.data.market_data import (
    DataQuality,
    ExecutionQuality,
    MarketSnapshot,
    ProviderStatus,
)
from src.execution.capital_admission import (
    CapitalAdmissionReason,
    CashBackedCapitalAdmissionPolicy,
)
from src.execution.capital_exposure import (
    CAPITAL_EXPOSURE_FX_FRESH_REQUIRED,
    BtcUsdtLongExposureCalculator,
    CapitalExposureReason,
)
from src.execution.models import OrderSide
from src.execution.slippage import (
    FixedBpsSlippage,
)
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
    18,
    14,
    0,
    tzinfo=timezone.utc,
)


def freshness_policy():
    return FxFreshnessPolicy(
        weekday_max_age_seconds=900.0,
        weekend_max_age_seconds=900.0,
    )


def converter():
    return CurrencyConverter(
        freshness_policy=(
            freshness_policy()
        ),
        clock=FixedClock(NOW),
    )


def calculator(
    *,
    slippage_bps=10.0,
):
    return BtcUsdtLongExposureCalculator(
        slippage_model=FixedBpsSlippage(
            slippage_bps
        ),
        fx_converter=converter(),
    )


def snapshot(
    *,
    asset_id="BTCUSDT",
    bid=100.0,
    ask=101.0,
    execution_quality=(
        ExecutionQuality.REAL_BOOK
    ),
):
    return MarketSnapshot(
        asset_id=asset_id,
        bid=bid,
        ask=ask,
        last=100.5,
        provider_timestamp=NOW,
        received_at=NOW,
        data_quality=DataQuality.REALTIME,
        delayed=False,
        quote_age_seconds=0.0,
        provider_status=(
            ProviderStatus.CONNECTED
        ),
        execution_quality=(
            execution_quality
        ),
    )


def quote(
    base,
    target,
    rate,
    *,
    age_seconds=0.0,
):
    return FxQuote(
        base_currency=base,
        quote_currency=target,
        rate=rate,
        provider="TEST",
        provider_timestamp=(
            NOW
            - timedelta(
                seconds=age_seconds
            )
        ),
        observed_at=NOW,
        source_quality=(
            FxSourceQuality.LIVE
        ),
    )


def fresh_fx(
    *,
    usdt_usd=0.999,
    usd_pln=4.0,
):
    return (
        quote(
            "USDT",
            "USD",
            usdt_usd,
        ),
        quote(
            "USD",
            "PLN",
            usd_pln,
        ),
    )


def test_calculates_btc_long_exposure_from_ask_slippage_and_two_fx_legs():
    result = calculator().calculate(
        market_snapshot=snapshot(),
        quantity="2",
        fx_quotes=fresh_fx(),
    )

    expected_price = (
        FixedBpsSlippage(10.0)
        .apply(
            101.0,
            OrderSide.BUY,
        )
    )

    expected_native = (
        Decimal(str(expected_price))
        * Decimal("2")
    )

    assert result.available is True
    assert (
        result.reason
        is CapitalExposureReason.AVAILABLE
    )
    assert (
        result.reference_price
        == Decimal("101.0")
    )
    assert (
        result.proposed_execution_price
        == Decimal(str(expected_price))
    )
    assert (
        result.native_notional
        == expected_native
    )
    assert result.native_currency == "USDT"
    assert result.fx_path == "USDT→USD→PLN"
    assert (
        result.fx_freshness
        is FxFreshness.FX_FRESH
    )

    expected_pln = (
        float(expected_native)
        * 0.999
        * 4.0
    )

    assert float(
        result.exposure_pln
    ) == pytest.approx(
        expected_pln
    )


def test_usdt_is_not_silently_equal_to_usd():
    depegged = calculator(
        slippage_bps=0.0
    ).calculate(
        market_snapshot=snapshot(
            bid=9.9,
            ask=10.0,
        ),
        quantity="10",
        fx_quotes=fresh_fx(
            usdt_usd=0.95,
            usd_pln=4.0,
        ),
    )

    assert depegged.available is True
    assert float(
        depegged.exposure_pln
    ) == pytest.approx(
        380.0
    )
    assert float(
        depegged.exposure_pln
    ) != pytest.approx(
        400.0
    )


def test_missing_usdtusd_leg_fails_closed():
    result = calculator().calculate(
        market_snapshot=snapshot(),
        quantity="1",
        fx_quotes=(
            quote(
                "USD",
                "PLN",
                4.0,
            ),
        ),
    )

    assert result.available is False
    assert (
        result.reason
        is CapitalExposureReason
        .FX_UNAVAILABLE
    )
    assert (
        result.unavailable_detail
        == "MISSING_FX_LEG:USDTUSD"
    )


def test_stale_fx_fails_closed_for_capital_admission():
    result = calculator().calculate(
        market_snapshot=snapshot(),
        quantity="1",
        fx_quotes=(
            quote(
                "USDT",
                "USD",
                1.0,
                age_seconds=900.0,
            ),
            quote(
                "USD",
                "PLN",
                4.0,
            ),
        ),
    )

    assert result.available is False
    assert (
        result.reason
        is CapitalExposureReason
        .FX_NOT_FRESH
    )
    assert (
        result.fx_freshness
        is FxFreshness.FX_STALE
    )
    assert (
        CAPITAL_EXPOSURE_FX_FRESH_REQUIRED
        in result.limitations
    )


def test_expired_fx_fails_closed():
    result = calculator().calculate(
        market_snapshot=snapshot(),
        quantity="1",
        fx_quotes=(
            quote(
                "USDT",
                "USD",
                1.0,
                age_seconds=(
                    96 * 60 * 60
                    + 1
                ),
            ),
            quote(
                "USD",
                "PLN",
                4.0,
            ),
        ),
    )

    assert result.available is False
    assert (
        result.reason
        is CapitalExposureReason
        .FX_UNAVAILABLE
    )


def test_future_fx_fails_closed():
    future_quote = FxQuote(
        base_currency="USDT",
        quote_currency="USD",
        rate=1.0,
        provider="TEST",
        provider_timestamp=(
            NOW
            + timedelta(
                seconds=1
            )
        ),
        observed_at=NOW,
        source_quality=(
            FxSourceQuality.LIVE
        ),
    )

    result = calculator().calculate(
        market_snapshot=snapshot(),
        quantity="1",
        fx_quotes=(
            future_quote,
            quote(
                "USD",
                "PLN",
                4.0,
            ),
        ),
    )

    assert result.available is False
    assert (
        result.reason
        is CapitalExposureReason
        .FX_UNAVAILABLE
    )
    assert (
        result.unavailable_detail
        == "FUTURE_FX_TIMESTAMP"
    )


def test_only_controlled_btcusdt_is_supported():
    result = calculator().calculate(
        market_snapshot=snapshot(
            asset_id="ETHUSDT",
        ),
        quantity="1",
        fx_quotes=fresh_fx(),
    )

    assert result.available is False
    assert (
        result.reason
        is CapitalExposureReason
        .ASSET_NOT_SUPPORTED
    )
    assert (
        result.unavailable_detail
        == "CONTROLLED_BTCUSDT_ONLY"
    )


def test_only_real_book_execution_quality_is_supported():
    result = calculator().calculate(
        market_snapshot=MarketSnapshot(
            asset_id="BTCUSDT",
            bid=None,
            ask=None,
            last=100.0,
            provider_timestamp=NOW,
            received_at=NOW,
            data_quality=(
                DataQuality.REALTIME
            ),
            delayed=False,
            quote_age_seconds=0.0,
            provider_status=(
                ProviderStatus.CONNECTED
            ),
            execution_quality=(
                ExecutionQuality
                .SIMULATED_SPREAD
            ),
        ),
        quantity="1",
        fx_quotes=fresh_fx(),
    )

    assert result.available is False
    assert (
        result.reason
        is CapitalExposureReason
        .EXECUTION_QUALITY_NOT_SUPPORTED
    )


@pytest.mark.parametrize(
    "quantity",
    [
        None,
        "0",
        "-1",
        "NaN",
        "Infinity",
        "not-a-number",
    ],
)
def test_invalid_quantity_fails_closed(
    quantity,
):
    result = calculator().calculate(
        market_snapshot=snapshot(),
        quantity=quantity,
        fx_quotes=fresh_fx(),
    )

    assert result.available is False
    assert (
        result.reason
        is CapitalExposureReason
        .QUANTITY_INVALID
    )


def test_duplicate_fx_pair_fails_closed():
    result = calculator().calculate(
        market_snapshot=snapshot(),
        quantity="1",
        fx_quotes=(
            quote(
                "USDT",
                "USD",
                1.0,
            ),
            quote(
                "USDT",
                "USD",
                0.99,
            ),
            quote(
                "USD",
                "PLN",
                4.0,
            ),
        ),
    )

    assert result.available is False
    assert (
        result.reason
        is CapitalExposureReason
        .FX_UNAVAILABLE
    )
    assert (
        "duplicate FX quote"
        in result.unavailable_detail
    )


def test_exposure_result_composes_with_cash_admission_core():
    exposure = calculator(
        slippage_bps=0.0
    ).calculate(
        market_snapshot=snapshot(
            bid=99.0,
            ask=100.0,
        ),
        quantity="2",
        fx_quotes=fresh_fx(
            usdt_usd=1.0,
            usd_pln=4.0,
        ),
    )

    assert exposure.available is True
    assert exposure.exposure_pln == Decimal(
        "800.0"
    )

    admitted = (
        CashBackedCapitalAdmissionPolicy()
        .evaluate_long_entry(
            settled_cash_pln="1000",
            proposed_exposure_pln=(
                exposure.exposure_pln
            ),
            max_exposure_percent="100",
        )
    )

    assert admitted.allowed is True
    assert (
        admitted.reason
        is CapitalAdmissionReason.ALLOWED
    )


def test_exposure_result_over_cash_limit_is_rejected_by_core():
    exposure = calculator(
        slippage_bps=0.0
    ).calculate(
        market_snapshot=snapshot(
            bid=99.0,
            ask=100.0,
        ),
        quantity="3",
        fx_quotes=fresh_fx(
            usdt_usd=1.0,
            usd_pln=4.0,
        ),
    )

    assert exposure.available is True
    assert exposure.exposure_pln == Decimal(
        "1200.0"
    )

    admitted = (
        CashBackedCapitalAdmissionPolicy()
        .evaluate_long_entry(
            settled_cash_pln="1000",
            proposed_exposure_pln=(
                exposure.exposure_pln
            ),
            max_exposure_percent="100",
        )
    )

    assert admitted.allowed is False
    assert (
        admitted.reason
        is CapitalAdmissionReason
        .CAPITAL_LIMIT_EXCEEDED
    )
