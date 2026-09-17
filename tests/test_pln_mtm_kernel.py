from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from src.accounting.mtm_kernel import (
    PlnMtmError,
    PlnUnrealizedMtmKernel,
)
from src.fx.models import FxFreshness


def test_long_marks_to_bid():
    result = PlnUnrealizedMtmKernel().calculate(
        accounting_id="mtm-long",
        asset_id="BTCUSDT",
        position_id="pos-long",
        side="LONG",
        native_currency="USDT",
        quantity="2",
        entry_price="100",
        bid="109",
        ask="110",
        pnl_multiplier="1",
        estimated_exit_fee_native="0",
        fx_freshness=FxFreshness.FX_FRESH,
        fx_rate="4",
        fx_path="USDTâ†’USDâ†’PLN",
        fx_quote_age_seconds="10",
    )

    assert result.mark_source == "BID"
    assert result.mark_price == Decimal("109")
    assert result.unrealized_pnl_native == Decimal("18")
    assert result.unrealized_pnl_pln == Decimal("72")


def test_short_marks_to_ask():
    result = PlnUnrealizedMtmKernel().calculate(
        accounting_id="mtm-short",
        asset_id="TEST",
        position_id="pos-short",
        side="SHORT",
        native_currency="USD",
        quantity="3",
        entry_price="100",
        bid="89",
        ask="90",
        pnl_multiplier="1",
        estimated_exit_fee_native="0",
        fx_freshness=FxFreshness.FX_FRESH,
        fx_rate="4",
        fx_path="USDâ†’PLN",
        fx_quote_age_seconds="5",
    )

    assert result.mark_source == "ASK"
    assert result.mark_price == Decimal("90")
    assert result.unrealized_pnl_native == Decimal("30")
    assert result.unrealized_pnl_pln == Decimal("120")


def test_estimated_exit_fee_is_separate_from_unrealized_pnl():
    result = PlnUnrealizedMtmKernel().calculate(
        accounting_id="mtm-fee",
        asset_id="TEST",
        position_id="pos-fee",
        side="LONG",
        native_currency="USD",
        quantity="2",
        entry_price="100",
        bid="110",
        ask="111",
        pnl_multiplier="1",
        estimated_exit_fee_native="0.44",
        fx_freshness=FxFreshness.FX_FRESH,
        fx_rate="4",
        fx_path="USDâ†’PLN",
        fx_quote_age_seconds="1",
    )

    assert result.unrealized_pnl_native == Decimal("20")
    assert result.estimated_exit_fee_native == Decimal("0.44")
    assert result.estimated_net_liquidation_pnl_native == Decimal("19.56")

    # A.8 does not silently redefine unrealized PnL as liquidation PnL.
    assert result.unrealized_pnl_native != (
        result.estimated_net_liquidation_pnl_native
    )

    assert result.unrealized_pnl_pln == Decimal("80")
    assert result.estimated_exit_fee_pln == Decimal("1.76")
    assert (
        result.estimated_net_liquidation_pnl_pln
        == Decimal("78.24")
    )


def test_stale_fx_still_exposes_pln_with_explicit_age():
    result = PlnUnrealizedMtmKernel().calculate(
        accounting_id="mtm-stale",
        asset_id="AAPL",
        position_id="pos-stale",
        side="LONG",
        native_currency="USD",
        quantity="1",
        entry_price="100",
        bid="105",
        ask="105.2",
        pnl_multiplier="1",
        estimated_exit_fee_native="0",
        fx_freshness=FxFreshness.FX_STALE,
        fx_rate="3.8",
        fx_path="USDâ†’PLN",
        fx_quote_age_seconds="7200",
    )

    assert result.pln_available is True
    assert result.fx_freshness is FxFreshness.FX_STALE
    assert result.fx_quote_age_seconds == Decimal("7200")
    assert result.unrealized_pnl_pln == Decimal("19.0")
    assert result.unavailable_reason is None


def test_stale_fx_requires_explicit_age():
    with pytest.raises(
        PlnMtmError,
        match="STALE_FX_REQUIRES_AGE",
    ):
        PlnUnrealizedMtmKernel().calculate(
            accounting_id="mtm-stale-age",
            asset_id="AAPL",
            position_id="pos-stale-age",
            side="LONG",
            native_currency="USD",
            quantity="1",
            entry_price="100",
            bid="105",
            ask="105.2",
            pnl_multiplier="1",
            estimated_exit_fee_native="0",
            fx_freshness=FxFreshness.FX_STALE,
            fx_rate="3.8",
            fx_path="USDâ†’PLN",
            fx_quote_age_seconds=None,
        )


def test_unavailable_fx_returns_native_but_no_pln():
    result = PlnUnrealizedMtmKernel().calculate(
        accounting_id="mtm-unavailable",
        asset_id="AAPL",
        position_id="pos-unavailable",
        side="LONG",
        native_currency="USD",
        quantity="1",
        entry_price="100",
        bid="105",
        ask="105.2",
        pnl_multiplier="1",
        estimated_exit_fee_native="0.1",
        fx_freshness=FxFreshness.FX_UNAVAILABLE,
        fx_rate=None,
        fx_path="USDâ†’PLN",
        fx_quote_age_seconds="400000",
        fx_unavailable_reason="FX_QUOTE_EXPIRED",
    )

    assert result.unrealized_pnl_native == Decimal("5")
    assert result.pln_available is False
    assert result.unrealized_pnl_pln is None
    assert result.estimated_exit_fee_pln is None
    assert result.estimated_net_liquidation_pnl_pln is None
    assert result.unavailable_reason == "FX_QUOTE_EXPIRED"


def test_unavailable_fx_requires_reason():
    with pytest.raises(
        PlnMtmError,
        match="FX_UNAVAILABLE_REASON_REQUIRED",
    ):
        PlnUnrealizedMtmKernel().calculate(
            accounting_id="mtm-unavailable-reason",
            asset_id="AAPL",
            position_id="pos-unavailable-reason",
            side="LONG",
            native_currency="USD",
            quantity="1",
            entry_price="100",
            bid="105",
            ask="105.2",
            pnl_multiplier="1",
            estimated_exit_fee_native="0",
            fx_freshness=FxFreshness.FX_UNAVAILABLE,
            fx_rate=None,
            fx_path="USDâ†’PLN",
            fx_quote_age_seconds="400000",
            fx_unavailable_reason=None,
        )


def test_unavailable_fx_rejects_rate_to_prevent_accidental_pln_use():
    with pytest.raises(
        PlnMtmError,
        match="FX_UNAVAILABLE_RATE_MUST_BE_NONE",
    ):
        PlnUnrealizedMtmKernel().calculate(
            accounting_id="mtm-unavailable-rate",
            asset_id="AAPL",
            position_id="pos-unavailable-rate",
            side="LONG",
            native_currency="USD",
            quantity="1",
            entry_price="100",
            bid="105",
            ask="105.2",
            pnl_multiplier="1",
            estimated_exit_fee_native="0",
            fx_freshness=FxFreshness.FX_UNAVAILABLE,
            fx_rate="3.8",
            fx_path="USDâ†’PLN",
            fx_quote_age_seconds="400000",
            fx_unavailable_reason="FX_QUOTE_EXPIRED",
        )


def test_pln_native_does_not_require_external_fx():
    result = PlnUnrealizedMtmKernel().calculate(
        accounting_id="mtm-pln",
        asset_id="PLN_ASSET",
        position_id="pos-pln",
        side="LONG",
        native_currency="PLN",
        quantity="2",
        entry_price="10",
        bid="12",
        ask="12.1",
        pnl_multiplier="1",
        estimated_exit_fee_native="0.5",
        fx_freshness=None,
        fx_rate=None,
        fx_path=None,
        fx_quote_age_seconds=None,
    )

    assert result.fx_freshness is FxFreshness.FX_FRESH
    assert result.fx_rate == Decimal("1")
    assert result.fx_path == "PLN"
    assert result.fx_quote_age_seconds == Decimal("0")
    assert result.unrealized_pnl_native == Decimal("4")
    assert result.unrealized_pnl_pln == Decimal("4")
    assert result.estimated_net_liquidation_pnl_pln == Decimal("3.5")


def test_decimal_boundary_uses_string_conversion():
    result = PlnUnrealizedMtmKernel().calculate(
        accounting_id="mtm-decimal",
        asset_id="BTCUSDT",
        position_id="pos-decimal",
        side="LONG",
        native_currency="USDT",
        quantity=0.1,
        entry_price=100.1,
        bid=100.9,
        ask=101.0,
        pnl_multiplier=1,
        estimated_exit_fee_native=0.01,
        fx_freshness=FxFreshness.FX_FRESH,
        fx_rate=3.7639,
        fx_path="USDTâ†’USDâ†’PLN",
        fx_quote_age_seconds=1.5,
    )

    assert result.quantity == Decimal("0.1")
    assert result.entry_price == Decimal("100.1")
    assert result.mark_price == Decimal("100.9")
    assert result.fx_rate == Decimal("3.7639")
    assert result.fx_quote_age_seconds == Decimal("1.5")
    assert result.unrealized_pnl_native == Decimal("0.08")


def test_multiplier_is_explicit():
    result = PlnUnrealizedMtmKernel().calculate(
        accounting_id="mtm-multiplier",
        asset_id="CONTRACT",
        position_id="pos-multiplier",
        side="LONG",
        native_currency="USD",
        quantity="2",
        entry_price="100",
        bid="101",
        ask="102",
        pnl_multiplier="100",
        estimated_exit_fee_native="5",
        fx_freshness=FxFreshness.FX_FRESH,
        fx_rate="1",
        fx_path="USDâ†’PLN",
        fx_quote_age_seconds="0",
    )

    assert result.unrealized_pnl_native == Decimal("200")
    assert result.estimated_exit_fee_native == Decimal("5")
    assert result.estimated_net_liquidation_pnl_native == Decimal("195")


@pytest.mark.parametrize(
    "field,value",
    [
        ("quantity", "0"),
        ("quantity", "-1"),
        ("entry_price", "0"),
        ("pnl_multiplier", "0"),
        ("pnl_multiplier", "-1"),
        ("estimated_exit_fee_native", "-1"),
    ],
)
def test_invalid_numeric_inputs_fail_closed(field, value):
    kwargs = {
        "accounting_id": "mtm-invalid",
        "asset_id": "TEST",
        "position_id": "pos-invalid",
        "side": "LONG",
        "native_currency": "USD",
        "quantity": "1",
        "entry_price": "100",
        "bid": "101",
        "ask": "102",
        "pnl_multiplier": "1",
        "estimated_exit_fee_native": "0",
        "fx_freshness": FxFreshness.FX_FRESH,
        "fx_rate": "4",
        "fx_path": "USDâ†’PLN",
        "fx_quote_age_seconds": "0",
    }

    kwargs[field] = value

    with pytest.raises(PlnMtmError):
        PlnUnrealizedMtmKernel().calculate(**kwargs)


def test_invalid_book_fails_closed():
    with pytest.raises(
        PlnMtmError,
        match="INVALID_BID_ASK",
    ):
        PlnUnrealizedMtmKernel().calculate(
            accounting_id="mtm-book",
            asset_id="TEST",
            position_id="pos-book",
            side="LONG",
            native_currency="USD",
            quantity="1",
            entry_price="100",
            bid="102",
            ask="101",
            pnl_multiplier="1",
            estimated_exit_fee_native="0",
            fx_freshness=FxFreshness.FX_FRESH,
            fx_rate="4",
            fx_path="USDâ†’PLN",
            fx_quote_age_seconds="0",
        )


def test_negative_fx_age_fails_closed():
    with pytest.raises(
        PlnMtmError,
        match="fx_quote_age_seconds cannot be negative",
    ):
        PlnUnrealizedMtmKernel().calculate(
            accounting_id="mtm-age",
            asset_id="TEST",
            position_id="pos-age",
            side="LONG",
            native_currency="USD",
            quantity="1",
            entry_price="100",
            bid="101",
            ask="102",
            pnl_multiplier="1",
            estimated_exit_fee_native="0",
            fx_freshness=FxFreshness.FX_FRESH,
            fx_rate="4",
            fx_path="USDâ†’PLN",
            fx_quote_age_seconds="-1",
        )


def test_available_fx_requires_rate_and_path():
    with pytest.raises(PlnMtmError):
        PlnUnrealizedMtmKernel().calculate(
            accounting_id="mtm-fx-required",
            asset_id="TEST",
            position_id="pos-fx-required",
            side="LONG",
            native_currency="USD",
            quantity="1",
            entry_price="100",
            bid="101",
            ask="102",
            pnl_multiplier="1",
            estimated_exit_fee_native="0",
            fx_freshness=FxFreshness.FX_FRESH,
            fx_rate=None,
            fx_path="USDâ†’PLN",
            fx_quote_age_seconds="0",
        )


def test_result_is_immutable():
    result = PlnUnrealizedMtmKernel().calculate(
        accounting_id="mtm-immutable",
        asset_id="TEST",
        position_id="pos-immutable",
        side="LONG",
        native_currency="USD",
        quantity="1",
        entry_price="100",
        bid="101",
        ask="102",
        pnl_multiplier="1",
        estimated_exit_fee_native="0",
        fx_freshness=FxFreshness.FX_FRESH,
        fx_rate="4",
        fx_path="USDâ†’PLN",
        fx_quote_age_seconds="0",
    )

    with pytest.raises(FrozenInstanceError):
        result.unrealized_pnl_native = Decimal("0")