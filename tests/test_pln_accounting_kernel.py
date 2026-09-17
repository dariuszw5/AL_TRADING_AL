from dataclasses import FrozenInstanceError
from decimal import Decimal
from types import SimpleNamespace

import pytest

from src.execution.models import OrderSide
from src.accounting.pln_kernel import (
    PlnAccountingError,
    PlnRealizedAccountingKernel,
)


def execution(
    *,
    execution_id,
    asset_id="TEST",
    side,
    quantity,
    reference_price,
    execution_price,
    bid,
    ask,
    slippage,
    fee,
):
    return SimpleNamespace(
        execution_id=execution_id,
        asset_id=asset_id,
        side=side,
        quantity=quantity,
        reference_price=reference_price,
        execution_price=execution_price,
        bid=bid,
        ask=ask,
        spread=float(ask) - float(bid),
        slippage=slippage,
        fee=fee,
    )


def test_long_price_pnl_uses_actual_execution_prices():
    entry = execution(
        execution_id="entry-1",
        side=OrderSide.BUY,
        quantity=2.0,
        reference_price=100.0,
        execution_price=100.0,
        bid=99.0,
        ask=100.0,
        slippage=0.0,
        fee=0.0,
    )

    exit_ = execution(
        execution_id="exit-1",
        side=OrderSide.SELL,
        quantity=2.0,
        reference_price=110.0,
        execution_price=110.0,
        bid=110.0,
        ask=111.0,
        slippage=0.0,
        fee=0.0,
    )

    result = PlnRealizedAccountingKernel().calculate(
        accounting_id="acct-1",
        position_id="pos-1",
        side="LONG",
        native_currency="USD",
        pnl_multiplier="1",
        fx_rate="4",
        fx_path="USDâ†’PLN",
        entry_execution=entry,
        exit_execution=exit_,
    )

    assert result.price_pnl_native == Decimal("20.00")
    assert result.fees_native == Decimal("0.0")
    assert result.net_realized_pnl_native == Decimal("20.00")
    assert result.net_realized_pnl_pln == Decimal("80.00")


def test_short_price_pnl_direction_is_correct():
    entry = execution(
        execution_id="entry-short",
        side=OrderSide.SELL,
        quantity=3,
        reference_price=100,
        execution_price=100,
        bid=100,
        ask=101,
        slippage=0,
        fee=0,
    )

    exit_ = execution(
        execution_id="exit-short",
        side=OrderSide.BUY,
        quantity=3,
        reference_price=90,
        execution_price=90,
        bid=89,
        ask=90,
        slippage=0,
        fee=0,
    )

    result = PlnRealizedAccountingKernel().calculate(
        accounting_id="acct-short",
        position_id="pos-short",
        side="SHORT",
        native_currency="USD",
        pnl_multiplier="1",
        fx_rate="4",
        fx_path="USDâ†’PLN",
        entry_execution=entry,
        exit_execution=exit_,
    )

    assert result.price_pnl_native == Decimal("30")
    assert result.net_realized_pnl_native == Decimal("30")
    assert result.net_realized_pnl_pln == Decimal("120")


def test_fees_are_subtracted_exactly_once():
    entry = execution(
        execution_id="entry-fee",
        side=OrderSide.BUY,
        quantity=2,
        reference_price=100,
        execution_price=100,
        bid=99,
        ask=100,
        slippage=0,
        fee=0.20,
    )

    exit_ = execution(
        execution_id="exit-fee",
        side=OrderSide.SELL,
        quantity=2,
        reference_price=110,
        execution_price=110,
        bid=110,
        ask=111,
        slippage=0,
        fee=0.22,
    )

    result = PlnRealizedAccountingKernel().calculate(
        accounting_id="acct-fee",
        position_id="pos-fee",
        side="LONG",
        native_currency="USD",
        pnl_multiplier="1",
        fx_rate="4",
        fx_path="USDâ†’PLN",
        entry_execution=entry,
        exit_execution=exit_,
    )

    assert result.price_pnl_native == Decimal("20")
    assert result.fees_native == Decimal("0.42")
    assert result.net_realized_pnl_native == Decimal("19.58")

    assert (
        result.price_pnl_native
        - result.fees_native
        == result.net_realized_pnl_native
    )

    assert result.fees_pln == Decimal("1.68")
    assert result.net_realized_pnl_pln == Decimal("78.32")


def test_spread_and_slippage_are_attribution_only():
    entry = execution(
        execution_id="entry-cost",
        side=OrderSide.BUY,
        quantity=2,
        reference_price=100,
        execution_price=100.1,
        bid=99,
        ask=100,
        slippage=0.1,
        fee=0.2002,
    )

    exit_ = execution(
        execution_id="exit-cost",
        side=OrderSide.SELL,
        quantity=2,
        reference_price=110,
        execution_price=109.9,
        bid=110,
        ask=111,
        slippage=0.1,
        fee=0.2198,
    )

    result = PlnRealizedAccountingKernel().calculate(
        accounting_id="acct-cost",
        position_id="pos-cost",
        side="LONG",
        native_currency="USD",
        pnl_multiplier="1",
        fx_rate="4",
        fx_path="USDâ†’PLN",
        entry_execution=entry,
        exit_execution=exit_,
    )

    assert result.price_pnl_native == Decimal("19.6")
    assert result.fees_native == Decimal("0.4200")
    assert result.net_realized_pnl_native == Decimal("19.1800")

    assert result.spread_cost_native == Decimal("2.0")
    assert result.slippage_cost_native == Decimal("0.4")

    assert result.spread_cost_pln == Decimal("8.0")
    assert result.slippage_cost_pln == Decimal("1.6")

    # Critical invariant:
    # spread and slippage already affected execution prices.
    # They must not be deducted a second time.
    assert result.net_realized_pnl_native == (
        result.price_pnl_native
        - result.fees_native
    )

    assert result.net_realized_pnl_native != (
        result.price_pnl_native
        - result.fees_native
        - result.spread_cost_native
        - result.slippage_cost_native
    )

    assert result.cost_attribution_only is True


def test_decimal_boundary_uses_string_conversion():
    entry = execution(
        execution_id="entry-decimal",
        side=OrderSide.BUY,
        quantity=1,
        reference_price=100,
        execution_price=100.1,
        bid=99.9,
        ask=100,
        slippage=0.1,
        fee=0.1,
    )

    exit_ = execution(
        execution_id="exit-decimal",
        side=OrderSide.SELL,
        quantity=1,
        reference_price=101,
        execution_price=100.9,
        bid=101,
        ask=101.1,
        slippage=0.1,
        fee=0.1,
    )

    result = PlnRealizedAccountingKernel().calculate(
        accounting_id="acct-decimal",
        position_id="pos-decimal",
        side="LONG",
        native_currency="USD",
        pnl_multiplier="1",
        fx_rate=3.7639,
        fx_path="USDâ†’PLN",
        entry_execution=entry,
        exit_execution=exit_,
    )

    assert result.fx_rate == Decimal("3.7639")
    assert result.price_pnl_native == Decimal("0.8")
    assert result.fees_native == Decimal("0.2")
    assert result.net_realized_pnl_native == Decimal("0.6")
    assert (
        result.net_realized_pnl_pln
        == Decimal("0.6") * Decimal("3.7639")
    )


def test_result_is_immutable():
    entry = execution(
        execution_id="entry-immutable",
        side=OrderSide.BUY,
        quantity=1,
        reference_price=100,
        execution_price=100,
        bid=99,
        ask=100,
        slippage=0,
        fee=0,
    )

    exit_ = execution(
        execution_id="exit-immutable",
        side=OrderSide.SELL,
        quantity=1,
        reference_price=101,
        execution_price=101,
        bid=101,
        ask=102,
        slippage=0,
        fee=0,
    )

    result = PlnRealizedAccountingKernel().calculate(
        accounting_id="acct-immutable",
        position_id="pos-immutable",
        side="LONG",
        native_currency="USD",
        pnl_multiplier="1",
        fx_rate="4",
        fx_path="USDâ†’PLN",
        entry_execution=entry,
        exit_execution=exit_,
    )

    with pytest.raises(FrozenInstanceError):
        result.net_realized_pnl_pln = Decimal("0")


def test_quantity_mismatch_fails_closed():
    entry = execution(
        execution_id="entry-q",
        side=OrderSide.BUY,
        quantity=1,
        reference_price=100,
        execution_price=100,
        bid=99,
        ask=100,
        slippage=0,
        fee=0,
    )

    exit_ = execution(
        execution_id="exit-q",
        side=OrderSide.SELL,
        quantity=2,
        reference_price=101,
        execution_price=101,
        bid=101,
        ask=102,
        slippage=0,
        fee=0,
    )

    with pytest.raises(
        PlnAccountingError,
        match="EXECUTION_QUANTITY_MISMATCH",
    ):
        PlnRealizedAccountingKernel().calculate(
            accounting_id="acct-q",
            position_id="pos-q",
            side="LONG",
            native_currency="USD",
            pnl_multiplier="1",
            fx_rate="4",
            fx_path="USDâ†’PLN",
            entry_execution=entry,
            exit_execution=exit_,
        )


def test_asset_mismatch_fails_closed():
    entry = execution(
        execution_id="entry-a",
        asset_id="AAA",
        side=OrderSide.BUY,
        quantity=1,
        reference_price=100,
        execution_price=100,
        bid=99,
        ask=100,
        slippage=0,
        fee=0,
    )

    exit_ = execution(
        execution_id="exit-a",
        asset_id="BBB",
        side=OrderSide.SELL,
        quantity=1,
        reference_price=101,
        execution_price=101,
        bid=101,
        ask=102,
        slippage=0,
        fee=0,
    )

    with pytest.raises(
        PlnAccountingError,
        match="EXECUTION_ASSET_MISMATCH",
    ):
        PlnRealizedAccountingKernel().calculate(
            accounting_id="acct-a",
            position_id="pos-a",
            side="LONG",
            native_currency="USD",
            pnl_multiplier="1",
            fx_rate="4",
            fx_path="USDâ†’PLN",
            entry_execution=entry,
            exit_execution=exit_,
        )


@pytest.mark.parametrize(
    "side,entry_side,exit_side",
    [
        ("LONG", OrderSide.SELL, OrderSide.BUY),
        ("SHORT", OrderSide.BUY, OrderSide.SELL),
    ],
)
def test_invalid_execution_direction_fails_closed(
    side,
    entry_side,
    exit_side,
):
    entry = execution(
        execution_id="entry-side",
        side=entry_side,
        quantity=1,
        reference_price=100,
        execution_price=100,
        bid=99,
        ask=100,
        slippage=0,
        fee=0,
    )

    exit_ = execution(
        execution_id="exit-side",
        side=exit_side,
        quantity=1,
        reference_price=101,
        execution_price=101,
        bid=101,
        ask=102,
        slippage=0,
        fee=0,
    )

    with pytest.raises(
        PlnAccountingError,
        match="EXECUTION_SIDE_MISMATCH",
    ):
        PlnRealizedAccountingKernel().calculate(
            accounting_id="acct-side",
            position_id="pos-side",
            side=side,
            native_currency="USD",
            pnl_multiplier="1",
            fx_rate="4",
            fx_path="USDâ†’PLN",
            entry_execution=entry,
            exit_execution=exit_,
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("pnl_multiplier", "0"),
        ("pnl_multiplier", "-1"),
        ("fx_rate", "0"),
        ("fx_rate", "-1"),
    ],
)
def test_positive_accounting_inputs_required(
    field,
    value,
):
    entry = execution(
        execution_id="entry-positive",
        side=OrderSide.BUY,
        quantity=1,
        reference_price=100,
        execution_price=100,
        bid=99,
        ask=100,
        slippage=0,
        fee=0,
    )

    exit_ = execution(
        execution_id="exit-positive",
        side=OrderSide.SELL,
        quantity=1,
        reference_price=101,
        execution_price=101,
        bid=101,
        ask=102,
        slippage=0,
        fee=0,
    )

    kwargs = {
        "accounting_id": "acct-positive",
        "position_id": "pos-positive",
        "side": "LONG",
        "native_currency": "USD",
        "pnl_multiplier": "1",
        "fx_rate": "4",
        "fx_path": "USDâ†’PLN",
        "entry_execution": entry,
        "exit_execution": exit_,
    }

    kwargs[field] = value

    with pytest.raises(
        PlnAccountingError,
        match=field,
    ):
        PlnRealizedAccountingKernel().calculate(
            **kwargs
        )


def test_negative_fee_fails_closed():
    entry = execution(
        execution_id="entry-negative-fee",
        side=OrderSide.BUY,
        quantity=1,
        reference_price=100,
        execution_price=100,
        bid=99,
        ask=100,
        slippage=0,
        fee=-1,
    )

    exit_ = execution(
        execution_id="exit-negative-fee",
        side=OrderSide.SELL,
        quantity=1,
        reference_price=101,
        execution_price=101,
        bid=101,
        ask=102,
        slippage=0,
        fee=0,
    )

    with pytest.raises(
        PlnAccountingError,
        match="fee cannot be negative",
    ):
        PlnRealizedAccountingKernel().calculate(
            accounting_id="acct-negative-fee",
            position_id="pos-negative-fee",
            side="LONG",
            native_currency="USD",
            pnl_multiplier="1",
            fx_rate="4",
            fx_path="USDâ†’PLN",
            entry_execution=entry,
            exit_execution=exit_,
        )


def test_invalid_book_fails_closed():
    entry = execution(
        execution_id="entry-book",
        side=OrderSide.BUY,
        quantity=1,
        reference_price=100,
        execution_price=100,
        bid=101,
        ask=100,
        slippage=0,
        fee=0,
    )

    exit_ = execution(
        execution_id="exit-book",
        side=OrderSide.SELL,
        quantity=1,
        reference_price=101,
        execution_price=101,
        bid=101,
        ask=102,
        slippage=0,
        fee=0,
    )

    with pytest.raises(
        PlnAccountingError,
        match="INVALID_BID_ASK",
    ):
        PlnRealizedAccountingKernel().calculate(
            accounting_id="acct-book",
            position_id="pos-book",
            side="LONG",
            native_currency="USD",
            pnl_multiplier="1",
            fx_rate="4",
            fx_path="USDâ†’PLN",
            entry_execution=entry,
            exit_execution=exit_,
        )


def test_multiplier_is_explicit_and_applied_to_price_costs():
    entry = execution(
        execution_id="entry-multiplier",
        side=OrderSide.BUY,
        quantity=1,
        reference_price=100,
        execution_price=100,
        bid=99,
        ask=100,
        slippage=0,
        fee=2,
    )

    exit_ = execution(
        execution_id="exit-multiplier",
        side=OrderSide.SELL,
        quantity=1,
        reference_price=101,
        execution_price=101,
        bid=101,
        ask=102,
        slippage=0,
        fee=3,
    )

    result = PlnRealizedAccountingKernel().calculate(
        accounting_id="acct-multiplier",
        position_id="pos-multiplier",
        side="LONG",
        native_currency="USD",
        pnl_multiplier="100",
        fx_rate="1",
        fx_path="USDâ†’PLN",
        entry_execution=entry,
        exit_execution=exit_,
    )

    assert result.price_pnl_native == Decimal("100")
    assert result.spread_cost_native == Decimal("100.0")

    # Execution.fee is already a monetary amount.
    # It must not be multiplied again.
    assert result.fees_native == Decimal("5")

    assert result.net_realized_pnl_native == Decimal("95")


def test_no_implicit_rounding_is_applied():
    entry = execution(
        execution_id="entry-round",
        side=OrderSide.BUY,
        quantity="0.12345678",
        reference_price="10.12345678",
        execution_price="10.12345678",
        bid="10.02345678",
        ask="10.12345678",
        slippage="0",
        fee="0.00000001",
    )

    exit_ = execution(
        execution_id="exit-round",
        side=OrderSide.SELL,
        quantity="0.12345678",
        reference_price="10.22345678",
        execution_price="10.22345678",
        bid="10.22345678",
        ask="10.32345678",
        slippage="0",
        fee="0.00000001",
    )

    result = PlnRealizedAccountingKernel().calculate(
        accounting_id="acct-round",
        position_id="pos-round",
        side="LONG",
        native_currency="USDT",
        pnl_multiplier="1",
        fx_rate="3.7639",
        fx_path="USDTâ†’USDâ†’PLN",
        entry_execution=entry,
        exit_execution=exit_,
    )

    expected = (
        Decimal("0.1")
        * Decimal("0.12345678")
        - Decimal("0.00000002")
    )

    assert result.net_realized_pnl_native == expected

    assert result.net_realized_pnl_pln == (
        expected
        * Decimal("3.7639")
    )
