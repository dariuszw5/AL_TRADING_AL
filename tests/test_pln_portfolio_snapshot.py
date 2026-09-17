from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from src.accounting.mtm_kernel import (
    PlnUnrealizedMtmKernel,
)
from src.accounting.portfolio_snapshot import (
    PlnPortfolioSnapshotError,
    PlnPortfolioSnapshotKernel,
)
from src.fx.models import FxFreshness


def mtm(
    *,
    accounting_id,
    asset_id,
    position_id,
    native_currency,
    quantity,
    entry_price,
    bid,
    ask,
    estimated_exit_fee_native,
    fx_freshness,
    fx_rate,
    fx_path,
    fx_quote_age_seconds,
    pnl_multiplier="1",
    fx_unavailable_reason=None,
):
    return PlnUnrealizedMtmKernel().calculate(
        accounting_id=accounting_id,
        asset_id=asset_id,
        position_id=position_id,
        side="LONG",
        native_currency=native_currency,
        quantity=quantity,
        entry_price=entry_price,
        bid=bid,
        ask=ask,
        pnl_multiplier=pnl_multiplier,
        estimated_exit_fee_native=(
            estimated_exit_fee_native
        ),
        fx_freshness=fx_freshness,
        fx_rate=fx_rate,
        fx_path=fx_path,
        fx_quote_age_seconds=(
            fx_quote_age_seconds
        ),
        fx_unavailable_reason=(
            fx_unavailable_reason
        ),
    )


def test_empty_portfolio_equals_cash():
    result = PlnPortfolioSnapshotKernel().calculate(
        cash_pln="1000",
        mtm_records=(),
    )

    assert result.cash_pln == Decimal("1000")
    assert result.position_count == 0
    assert result.unrealized_pnl_pln == Decimal("0")
    assert (
        result.estimated_exit_fees_pln
        == Decimal("0")
    )
    assert (
        result.estimated_net_liquidation_pnl_pln
        == Decimal("0")
    )
    assert result.equity_pln == Decimal("1000")
    assert (
        result.estimated_liquidation_equity_pln
        == Decimal("1000")
    )
    assert result.exposure_pln == Decimal("0")
    assert result.pln_available is True
    assert (
        result.fx_freshness
        is FxFreshness.FX_FRESH
    )
    assert (
        result.max_fx_quote_age_seconds
        == Decimal("0")
    )


def test_equity_uses_price_mtm_and_liquidation_equity_uses_exit_fee():
    record = mtm(
        accounting_id="mtm-btc",
        asset_id="BTCUSDT",
        position_id="pos-btc",
        native_currency="USDT",
        quantity="2",
        entry_price="100",
        bid="109",
        ask="110",
        estimated_exit_fee_native="0.44",
        fx_freshness=FxFreshness.FX_FRESH,
        fx_rate="4",
        fx_path="USDTâ†’USDâ†’PLN",
        fx_quote_age_seconds="10",
    )

    result = PlnPortfolioSnapshotKernel().calculate(
        cash_pln="1000",
        mtm_records=(record,),
    )

    # Price MTM is 18 USDT -> 72 PLN.
    assert result.unrealized_pnl_pln == Decimal("72")

    # Future exit fee remains separate.
    assert (
        result.estimated_exit_fees_pln
        == Decimal("1.76")
    )
    assert (
        result.estimated_net_liquidation_pnl_pln
        == Decimal("70.24")
    )

    # Normal equity does not silently pre-charge a future fee.
    assert result.equity_pln == Decimal("1072")

    # Close-now estimate does.
    assert (
        result.estimated_liquidation_equity_pln
        == Decimal("1070.24")
    )

    # Exposure is mark-side notional, not PnL.
    assert result.exposure_pln == Decimal("872")


def test_cash_is_caller_supplied_and_not_rebuilt_from_trade_history():
    record = mtm(
        accounting_id="mtm-cash",
        asset_id="AAPL",
        position_id="pos-cash",
        native_currency="USD",
        quantity="1",
        entry_price="100",
        bid="105",
        ask="105.2",
        estimated_exit_fee_native="0.1",
        fx_freshness=FxFreshness.FX_FRESH,
        fx_rate="4",
        fx_path="USDâ†’PLN",
        fx_quote_age_seconds="1",
    )

    result = PlnPortfolioSnapshotKernel().calculate(
        cash_pln="912.345",
        mtm_records=(record,),
    )

    assert result.cash_pln == Decimal("912.345")


def test_stale_fx_keeps_portfolio_pln_with_explicit_quality_and_age():
    fresh = mtm(
        accounting_id="mtm-fresh",
        asset_id="BTCUSDT",
        position_id="pos-fresh",
        native_currency="USDT",
        quantity="2",
        entry_price="100",
        bid="109",
        ask="110",
        estimated_exit_fee_native="0.44",
        fx_freshness=FxFreshness.FX_FRESH,
        fx_rate="4",
        fx_path="USDTâ†’USDâ†’PLN",
        fx_quote_age_seconds="10",
    )

    stale = mtm(
        accounting_id="mtm-stale",
        asset_id="AAPL",
        position_id="pos-stale",
        native_currency="USD",
        quantity="1",
        entry_price="100",
        bid="105",
        ask="105.2",
        estimated_exit_fee_native="0.1",
        fx_freshness=FxFreshness.FX_STALE,
        fx_rate="3.8",
        fx_path="USDâ†’PLN",
        fx_quote_age_seconds="7200",
    )

    result = PlnPortfolioSnapshotKernel().calculate(
        cash_pln="1000",
        mtm_records=(fresh, stale),
    )

    assert result.pln_available is True
    assert (
        result.fx_freshness
        is FxFreshness.FX_STALE
    )
    assert (
        result.max_fx_quote_age_seconds
        == Decimal("7200")
    )
    assert result.stale_assets == ("AAPL",)
    assert result.unavailable_assets == ()

    assert result.unrealized_pnl_pln == Decimal("91.0")
    assert (
        result.estimated_exit_fees_pln
        == Decimal("2.14")
    )
    assert (
        result.estimated_net_liquidation_pnl_pln
        == Decimal("88.86")
    )
    assert result.equity_pln == Decimal("1091.0")
    assert (
        result.estimated_liquidation_equity_pln
        == Decimal("1088.86")
    )
    assert result.exposure_pln == Decimal("1271.0")


def test_unavailable_fx_makes_portfolio_pln_totals_unavailable():
    unavailable = mtm(
        accounting_id="mtm-unavailable",
        asset_id="AAPL",
        position_id="pos-unavailable",
        native_currency="USD",
        quantity="1",
        entry_price="100",
        bid="105",
        ask="105.2",
        estimated_exit_fee_native="0.1",
        fx_freshness=FxFreshness.FX_UNAVAILABLE,
        fx_rate=None,
        fx_path="USDâ†’PLN",
        fx_quote_age_seconds="400000",
        fx_unavailable_reason="FX_QUOTE_EXPIRED",
    )

    result = PlnPortfolioSnapshotKernel().calculate(
        cash_pln="1000",
        mtm_records=(unavailable,),
    )

    # Settled PLN cash is still known.
    assert result.cash_pln == Decimal("1000")

    # But the portfolio PLN valuation is deliberately incomplete,
    # so aggregate values are not silently computed from a subset.
    assert result.pln_available is False
    assert (
        result.fx_freshness
        is FxFreshness.FX_UNAVAILABLE
    )
    assert result.unrealized_pnl_pln is None
    assert result.estimated_exit_fees_pln is None
    assert (
        result.estimated_net_liquidation_pnl_pln
        is None
    )
    assert result.equity_pln is None
    assert (
        result.estimated_liquidation_equity_pln
        is None
    )
    assert result.exposure_pln is None
    assert result.unavailable_assets == ("AAPL",)
    assert (
        "PORTFOLIO_PLN_INCOMPLETE_DUE_TO_FX"
        in result.limitations
    )


def test_unavailable_asset_prevents_partial_portfolio_total():
    fresh = mtm(
        accounting_id="mtm-ok",
        asset_id="BTCUSDT",
        position_id="pos-ok",
        native_currency="USDT",
        quantity="1",
        entry_price="100",
        bid="110",
        ask="111",
        estimated_exit_fee_native="0",
        fx_freshness=FxFreshness.FX_FRESH,
        fx_rate="4",
        fx_path="USDTâ†’USDâ†’PLN",
        fx_quote_age_seconds="10",
    )

    unavailable = mtm(
        accounting_id="mtm-bad",
        asset_id="AAPL",
        position_id="pos-bad",
        native_currency="USD",
        quantity="1",
        entry_price="100",
        bid="105",
        ask="105.2",
        estimated_exit_fee_native="0",
        fx_freshness=FxFreshness.FX_UNAVAILABLE,
        fx_rate=None,
        fx_path="USDâ†’PLN",
        fx_quote_age_seconds="400000",
        fx_unavailable_reason="FX_QUOTE_EXPIRED",
    )

    result = PlnPortfolioSnapshotKernel().calculate(
        cash_pln="1000",
        mtm_records=(fresh, unavailable),
    )

    assert result.pln_available is False
    assert result.equity_pln is None
    assert result.exposure_pln is None


def test_duplicate_position_id_fails_closed():
    first = mtm(
        accounting_id="mtm-1",
        asset_id="AAPL",
        position_id="same-position",
        native_currency="USD",
        quantity="1",
        entry_price="100",
        bid="101",
        ask="102",
        estimated_exit_fee_native="0",
        fx_freshness=FxFreshness.FX_FRESH,
        fx_rate="4",
        fx_path="USDâ†’PLN",
        fx_quote_age_seconds="0",
    )

    second = mtm(
        accounting_id="mtm-2",
        asset_id="AAPL",
        position_id="same-position",
        native_currency="USD",
        quantity="1",
        entry_price="100",
        bid="102",
        ask="103",
        estimated_exit_fee_native="0",
        fx_freshness=FxFreshness.FX_FRESH,
        fx_rate="4",
        fx_path="USDâ†’PLN",
        fx_quote_age_seconds="0",
    )

    with pytest.raises(
        PlnPortfolioSnapshotError,
        match="DUPLICATE_POSITION_ID",
    ):
        PlnPortfolioSnapshotKernel().calculate(
            cash_pln="1000",
            mtm_records=(first, second),
        )


def test_contract_multiplier_mismatch_fails_closed():
    record = mtm(
        accounting_id="mtm-mismatch",
        asset_id="BTCUSDT",
        position_id="pos-mismatch",
        native_currency="USDT",
        quantity="1",
        entry_price="100",
        bid="101",
        ask="102",
        estimated_exit_fee_native="0",
        fx_freshness=FxFreshness.FX_FRESH,
        fx_rate="4",
        fx_path="USDTâ†’USDâ†’PLN",
        fx_quote_age_seconds="0",
        pnl_multiplier="2",
    )

    with pytest.raises(
        PlnPortfolioSnapshotError,
        match="PNL_MULTIPLIER_MISMATCH",
    ):
        PlnPortfolioSnapshotKernel().calculate(
            cash_pln="1000",
            mtm_records=(record,),
        )


def test_native_currency_mismatch_fails_closed():
    record = mtm(
        accounting_id="mtm-currency",
        asset_id="AAPL",
        position_id="pos-currency",
        native_currency="USDT",
        quantity="1",
        entry_price="100",
        bid="101",
        ask="102",
        estimated_exit_fee_native="0",
        fx_freshness=FxFreshness.FX_FRESH,
        fx_rate="4",
        fx_path="USDTâ†’USDâ†’PLN",
        fx_quote_age_seconds="0",
    )

    with pytest.raises(
        PlnPortfolioSnapshotError,
        match="NATIVE_CURRENCY_MISMATCH",
    ):
        PlnPortfolioSnapshotKernel().calculate(
            cash_pln="1000",
            mtm_records=(record,),
        )


def test_blocked_futures_contract_fails_closed_even_with_manual_mtm():
    record = mtm(
        accounting_id="mtm-gold",
        asset_id="GOLD_FUT_CONT",
        position_id="pos-gold",
        native_currency="USD",
        quantity="1",
        entry_price="2000",
        bid="2010",
        ask="2011",
        estimated_exit_fee_native="0",
        fx_freshness=FxFreshness.FX_FRESH,
        fx_rate="4",
        fx_path="USDâ†’PLN",
        fx_quote_age_seconds="0",
        pnl_multiplier="100",
    )

    with pytest.raises(
        PlnPortfolioSnapshotError,
        match="ACCOUNTING_CONTRACT_BLOCKED",
    ):
        PlnPortfolioSnapshotKernel().calculate(
            cash_pln="1000",
            mtm_records=(record,),
        )


@pytest.mark.parametrize(
    "cash_pln",
    [
        "NaN",
        "Infinity",
        "-Infinity",
    ],
)
def test_nonfinite_cash_fails_closed(cash_pln):
    with pytest.raises(
        PlnPortfolioSnapshotError,
        match="cash_pln must be a finite decimal",
    ):
        PlnPortfolioSnapshotKernel().calculate(
            cash_pln=cash_pln,
            mtm_records=(),
        )


def test_negative_cash_is_explicitly_supported():
    result = PlnPortfolioSnapshotKernel().calculate(
        cash_pln="-100.25",
        mtm_records=(),
    )

    assert result.cash_pln == Decimal("-100.25")
    assert result.equity_pln == Decimal("-100.25")


def test_decimal_string_boundary_is_preserved():
    record = mtm(
        accounting_id="mtm-decimal",
        asset_id="AAPL",
        position_id="pos-decimal",
        native_currency="USD",
        quantity=0.1,
        entry_price=100.1,
        bid=100.9,
        ask=101.0,
        estimated_exit_fee_native=0.01,
        fx_freshness=FxFreshness.FX_FRESH,
        fx_rate=3.7639,
        fx_path="USDâ†’PLN",
        fx_quote_age_seconds=1.5,
    )

    result = PlnPortfolioSnapshotKernel().calculate(
        cash_pln=1000.1,
        mtm_records=(record,),
    )

    assert result.cash_pln == Decimal("1000.1")
    assert isinstance(result.exposure_pln, Decimal)
    assert isinstance(result.equity_pln, Decimal)


def test_result_is_immutable():
    result = PlnPortfolioSnapshotKernel().calculate(
        cash_pln="1000",
        mtm_records=(),
    )

    with pytest.raises(FrozenInstanceError):
        result.cash_pln = Decimal("0")