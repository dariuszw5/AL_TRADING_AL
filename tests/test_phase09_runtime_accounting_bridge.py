from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest

from src.accounting.instrument_contracts import (
    InstrumentAccountingContractError,
)
from src.accounting.runtime_bridge import (
    ACCOUNTING_PERSISTENCE_LIMITATION,
    Phase09RuntimeAccountingBridge,
    RuntimeAccountingBridgeError,
)
from src.fx.models import (
    FxConversionResult,
    FxFreshness,
    FxPath,
    FxQuote,
    FxSourceQuality,
)
from src.fx.realized_booking import (
    RealizedFxBooker,
)
from src.fx.realized_selection import (
    RealizedFxSelectionPolicy,
)


UTC = timezone.utc
ARROW = "\u2192"

CLOSED_AT = datetime(
    2026,
    9,
    17,
    12,
    0,
    tzinfo=UTC,
)

BOOKED_AT = datetime(
    2026,
    9,
    17,
    13,
    0,
    tzinfo=UTC,
)


class FixedClock:
    def now(self):
        return BOOKED_AT


def position(
    *,
    asset_id="BTCUSDT",
    side="LONG",
    position_id="pos-1",
    quantity=2.0,
    entry_execution_id="exec-entry",
    entry_price=100.0,
    closed_at=None,
    exit_execution_id=None,
):
    return SimpleNamespace(
        position_id=position_id,
        asset_id=asset_id,
        side=side,
        quantity=quantity,
        entry_execution_id=(
            entry_execution_id
        ),
        entry_price=entry_price,
        closed_at=closed_at,
        exit_execution_id=(
            exit_execution_id
        ),
    )


def snapshot(
    *,
    asset_id="BTCUSDT",
    bid=109.0,
    ask=110.0,
):
    return SimpleNamespace(
        asset_id=asset_id,
        bid=bid,
        ask=ask,
    )


def conversion(
    *,
    source_currency="USDT",
    rate=4.0,
    freshness=FxFreshness.FX_FRESH,
    age=10.0,
    unavailable_reason=None,
):
    if source_currency == "USDT":
        currencies = (
            "USDT",
            "USD",
            "PLN",
        )
    elif source_currency == "USD":
        currencies = (
            "USD",
            "PLN",
        )
    elif source_currency == "EUR":
        currencies = (
            "EUR",
            "PLN",
        )
    else:
        currencies = (
            source_currency,
            "PLN",
        )

    return FxConversionResult(
        source_amount=1.0,
        source_currency=(
            source_currency
        ),
        target_currency="PLN",
        converted_amount=rate,
        fx_path=FxPath(
            currencies
        ),
        freshness=freshness,
        quote_age_seconds=age,
        legs=(),
        limitations=(
            "KNOWN_LIMITATION: "
            "FX_CONVERSION_COST_NOT_MODELLED",
        ),
        unavailable_reason=(
            unavailable_reason
        ),
    )


def execution(
    *,
    execution_id,
    asset_id="AAPL",
    side="BUY",
    quantity=2.0,
    execution_price=100.0,
    bid=99.9,
    ask=100.0,
    slippage=0.0,
    fee=0.2,
):
    return SimpleNamespace(
        execution_id=execution_id,
        asset_id=asset_id,
        side=side,
        quantity=quantity,
        execution_price=(
            execution_price
        ),
        bid=bid,
        ask=ask,
        slippage=slippage,
        fee=fee,
    )


def aapl_bridge():
    return Phase09RuntimeAccountingBridge(
        fx_enabled=True,
        pln_accounting_enabled=True,
        realized_fx_selection_policy=(
            RealizedFxSelectionPolicy(
                market_max_age_seconds=7200,
                daily_reference_max_age_days=7,
            )
        ),
        realized_fx_booker=(
            RealizedFxBooker(
                clock=FixedClock()
            )
        ),
    )


def nbp_usd_prior_day():
    return FxQuote(
        base_currency="USD",
        quote_currency="PLN",
        rate=4.0,
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
    )


def test_pln_flag_off_fails_closed():
    bridge = Phase09RuntimeAccountingBridge(
        fx_enabled=True,
        pln_accounting_enabled=False,
    )

    with pytest.raises(
        RuntimeAccountingBridgeError,
        match="PLN_ACCOUNTING_DISABLED",
    ):
        bridge.mark_position(
            position=position(),
            market_snapshot=snapshot(),
            fx_conversion=conversion(),
            estimated_exit_fee_native="0",
        )


def test_fx_flag_off_fails_closed_for_usdt():
    bridge = Phase09RuntimeAccountingBridge(
        fx_enabled=False,
        pln_accounting_enabled=True,
    )

    with pytest.raises(
        RuntimeAccountingBridgeError,
        match="FX_ACCOUNTING_DISABLED",
    ):
        bridge.mark_position(
            position=position(),
            market_snapshot=snapshot(),
            fx_conversion=conversion(),
            estimated_exit_fee_native="0",
        )


def test_btc_mtm_uses_verified_instrument_contract_and_unit_fx_rate():
    bridge = Phase09RuntimeAccountingBridge(
        fx_enabled=True,
        pln_accounting_enabled=True,
    )

    result = bridge.mark_position(
        position=position(),
        market_snapshot=snapshot(),
        fx_conversion=conversion(),
        estimated_exit_fee_native="0.44",
    )

    assert result.native_currency == "USDT"
    assert result.pnl_multiplier == Decimal("1")
    assert result.mark_source == "BID"
    assert result.mark_price == Decimal("109.0")
    assert result.unrealized_pnl_native == Decimal("18.0")
    assert result.unrealized_pnl_pln == Decimal("72.00")
    assert (
        result.estimated_net_liquidation_pnl_pln
        == Decimal("70.24")
    )


def test_mtm_accepts_explicit_stale_fx_and_preserves_stale_state():
    bridge = Phase09RuntimeAccountingBridge(
        fx_enabled=True,
        pln_accounting_enabled=True,
    )

    result = bridge.mark_position(
        position=position(
            asset_id="AAPL",
            quantity=1.0,
        ),
        market_snapshot=snapshot(
            asset_id="AAPL",
            bid=105.0,
            ask=105.2,
        ),
        fx_conversion=conversion(
            source_currency="USD",
            rate=3.8,
            freshness=(
                FxFreshness.FX_STALE
            ),
            age=7200.0,
        ),
        estimated_exit_fee_native="0",
    )

    assert result.fx_freshness is FxFreshness.FX_STALE
    assert result.fx_quote_age_seconds == Decimal("7200.0")
    assert result.unrealized_pnl_pln == Decimal("19.00")


def test_mtm_unavailable_fx_keeps_native_and_hides_pln():
    bridge = Phase09RuntimeAccountingBridge(
        fx_enabled=True,
        pln_accounting_enabled=True,
    )

    result = bridge.mark_position(
        position=position(
            asset_id="AAPL",
            quantity=1.0,
        ),
        market_snapshot=snapshot(
            asset_id="AAPL",
            bid=105.0,
            ask=105.2,
        ),
        fx_conversion=conversion(
            source_currency="USD",
            rate=None,
            freshness=(
                FxFreshness.FX_UNAVAILABLE
            ),
            age=400000.0,
            unavailable_reason=(
                "FX_QUOTE_EXPIRED"
            ),
        ),
        estimated_exit_fee_native="0.1",
    )

    assert result.unrealized_pnl_native == Decimal("5.0")
    assert result.pln_available is False
    assert result.unrealized_pnl_pln is None
    assert result.unavailable_reason == "FX_QUOTE_EXPIRED"


def test_mtm_rejects_non_unit_fx_conversion():
    bridge = Phase09RuntimeAccountingBridge(
        fx_enabled=True,
        pln_accounting_enabled=True,
    )

    fx = SimpleNamespace(
        source_amount=2.0,
        source_currency="USDT",
        target_currency="PLN",
        converted_amount=8.0,
        fx_path=FxPath(
            (
                "USDT",
                "USD",
                "PLN",
            )
        ),
        freshness=FxFreshness.FX_FRESH,
        quote_age_seconds=10.0,
        unavailable_reason=None,
    )

    with pytest.raises(
        RuntimeAccountingBridgeError,
        match="FX_CONVERSION_MUST_BE_UNIT_RATE",
    ):
        bridge.mark_position(
            position=position(),
            market_snapshot=snapshot(),
            fx_conversion=fx,
            estimated_exit_fee_native="0",
        )


def test_mtm_rejects_snapshot_asset_mismatch():
    bridge = Phase09RuntimeAccountingBridge(
        fx_enabled=True,
        pln_accounting_enabled=True,
    )

    with pytest.raises(
        RuntimeAccountingBridgeError,
        match="MARKET_SNAPSHOT_ASSET_MISMATCH",
    ):
        bridge.mark_position(
            position=position(),
            market_snapshot=snapshot(
                asset_id="ETHUSDT"
            ),
            fx_conversion=conversion(),
            estimated_exit_fee_native="0",
        )


@pytest.mark.parametrize(
    "asset_id",
    [
        "GOLD_FUT_CONT",
        "WTI_FUT_CONT",
    ],
)
def test_continuous_futures_remain_fail_closed(asset_id):
    bridge = Phase09RuntimeAccountingBridge(
        fx_enabled=True,
        pln_accounting_enabled=True,
    )

    with pytest.raises(
        InstrumentAccountingContractError,
        match="ACCOUNTING_CONTRACT_BLOCKED",
    ):
        bridge.mark_position(
            position=position(
                asset_id=asset_id,
            ),
            market_snapshot=snapshot(
                asset_id=asset_id,
            ),
            fx_conversion=conversion(
                source_currency="USD",
            ),
            estimated_exit_fee_native="0",
        )


def test_realized_requires_full_entry_execution():
    bridge = aapl_bridge()

    closed_position = position(
        asset_id="AAPL",
        position_id="pos-aapl",
        quantity=2.0,
        entry_execution_id="entry-aapl",
        entry_price=100.0,
        closed_at=CLOSED_AT,
        exit_execution_id="exit-aapl",
    )

    exit_execution = execution(
        execution_id="exit-aapl",
        side="SELL",
        execution_price=110.0,
        bid=110.0,
        ask=110.1,
        fee=0.22,
    )

    with pytest.raises(
        RuntimeAccountingBridgeError,
        match="ENTRY_EXECUTION_REQUIRED",
    ):
        bridge.book_realized(
            position=closed_position,
            entry_execution=None,
            exit_execution=exit_execution,
            fx_quotes=(
                nbp_usd_prior_day(),
            ),
        )


def test_realized_uses_full_executions_and_selected_fx_evidence():
    bridge = aapl_bridge()

    closed_position = position(
        asset_id="AAPL",
        position_id="pos-aapl",
        quantity=2.0,
        entry_execution_id="entry-aapl",
        entry_price=100.0,
        closed_at=CLOSED_AT,
        exit_execution_id="exit-aapl",
    )

    entry_execution = execution(
        execution_id="entry-aapl",
        side="BUY",
        execution_price=100.0,
        bid=99.9,
        ask=100.0,
        fee=0.2,
    )

    exit_execution = execution(
        execution_id="exit-aapl",
        side="SELL",
        execution_price=110.0,
        bid=110.0,
        ask=110.1,
        fee=0.22,
    )

    result = bridge.book_realized(
        position=closed_position,
        entry_execution=entry_execution,
        exit_execution=exit_execution,
        fx_quotes=(
            nbp_usd_prior_day(),
        ),
    )

    accounting = (
        result.accounting_record
    )

    booking = result.fx_booking

    assert accounting.net_realized_pnl_native == Decimal("19.58")
    assert accounting.fx_rate == Decimal("4.0")
    assert accounting.fx_path == f"USD{ARROW}PLN"
    assert accounting.net_realized_pnl_pln == Decimal("78.320")

    assert booking.fx_provider == "NBP_TABLE_A"
    assert booking.fx_table == "180/A/NBP/2026"
    assert booking.fx_effective_date == date(2026, 9, 16)
    assert booking.fx_path == f"USD{ARROW}PLN"

    assert (
        ACCOUNTING_PERSISTENCE_LIMITATION
        in result.limitations
    )


def test_realized_rejects_entry_execution_id_mismatch():
    bridge = aapl_bridge()

    closed_position = position(
        asset_id="AAPL",
        position_id="pos-aapl",
        quantity=2.0,
        entry_execution_id="expected-entry",
        entry_price=100.0,
        closed_at=CLOSED_AT,
        exit_execution_id="exit-aapl",
    )

    with pytest.raises(
        RuntimeAccountingBridgeError,
        match="ENTRY_EXECUTION_MISMATCH",
    ):
        bridge.book_realized(
            position=closed_position,
            entry_execution=execution(
                execution_id="other-entry",
                side="BUY",
            ),
            exit_execution=execution(
                execution_id="exit-aapl",
                side="SELL",
                execution_price=110.0,
                bid=110.0,
                ask=110.1,
            ),
            fx_quotes=(
                nbp_usd_prior_day(),
            ),
        )


def test_portfolio_snapshot_delegates_to_a10_kernel():
    bridge = Phase09RuntimeAccountingBridge(
        fx_enabled=True,
        pln_accounting_enabled=True,
    )

    mtm = bridge.mark_position(
        position=position(),
        market_snapshot=snapshot(),
        fx_conversion=conversion(),
        estimated_exit_fee_native="0.44",
    )

    result = bridge.portfolio_snapshot(
        cash_pln="1000",
        mtm_records=(mtm,),
    )

    assert result.cash_pln == Decimal("1000")
    assert result.position_count == 1
    assert result.unrealized_pnl_pln == Decimal("72.00")
    assert result.equity_pln == Decimal("1072.00")
    assert (
        result.estimated_liquidation_equity_pln
        == Decimal("1070.24")
    )