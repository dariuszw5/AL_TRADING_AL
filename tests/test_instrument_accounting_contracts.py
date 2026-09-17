from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from src.accounting.instrument_contracts import (
    AccountingContractStatus,
    InstrumentAccountingContractError,
    QuantitySemantics,
    get_instrument_accounting_contract,
    list_instrument_accounting_contracts,
    require_runtime_accounting_contract,
)
from src.data.assets import get_asset


TARGET_ASSETS = {
    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT",
    "BNBUSDT",
    "XRPUSDT",
    "EURUSD",
    "GOLD_FUT_CONT",
    "WTI_FUT_CONT",
    "AAPL",
}


def test_contract_registry_covers_exact_target_assets():
    contracts = list_instrument_accounting_contracts()

    assert {item.asset_id for item in contracts} == TARGET_ASSETS


@pytest.mark.parametrize(
    "asset_id,native_currency,quantity_semantics",
    [
        (
            "BTCUSDT",
            "USDT",
            QuantitySemantics.BASE_UNITS,
        ),
        (
            "ETHUSDT",
            "USDT",
            QuantitySemantics.BASE_UNITS,
        ),
        (
            "SOLUSDT",
            "USDT",
            QuantitySemantics.BASE_UNITS,
        ),
        (
            "BNBUSDT",
            "USDT",
            QuantitySemantics.BASE_UNITS,
        ),
        (
            "XRPUSDT",
            "USDT",
            QuantitySemantics.BASE_UNITS,
        ),
        (
            "EURUSD",
            "USD",
            QuantitySemantics.BASE_UNITS,
        ),
        (
            "AAPL",
            "USD",
            QuantitySemantics.SHARES,
        ),
    ],
)
def test_unit_based_assets_are_runtime_accounting_ready(
    asset_id,
    native_currency,
    quantity_semantics,
):
    contract = require_runtime_accounting_contract(
        asset_id
    )

    assert contract.status is AccountingContractStatus.READY
    assert contract.runtime_accounting_ready is True
    assert contract.native_pnl_currency == native_currency
    assert contract.quantity_semantics is quantity_semantics
    assert contract.pnl_multiplier == Decimal("1")
    assert contract.reference_contract_multiplier is None


@pytest.mark.parametrize(
    "asset_id",
    [
        "BTCUSDT",
        "ETHUSDT",
        "SOLUSDT",
        "BNBUSDT",
        "XRPUSDT",
        "EURUSD",
        "AAPL",
    ],
)
def test_ready_contract_matches_asset_registry(asset_id):
    asset = get_asset(asset_id)
    contract = get_instrument_accounting_contract(
        asset_id
    )

    assert contract.instrument_type == asset.instrument_type
    assert contract.native_pnl_currency == asset.quote_currency


@pytest.mark.parametrize(
    "asset_id,quantity,price,expected",
    [
        (
            "BTCUSDT",
            "0.25",
            "100000",
            Decimal("25000.00"),
        ),
        (
            "EURUSD",
            "1000",
            "1.1",
            Decimal("1100.0"),
        ),
        (
            "AAPL",
            "2",
            "250",
            Decimal("500"),
        ),
    ],
)
def test_ready_native_notional_is_price_times_quantity(
    asset_id,
    quantity,
    price,
    expected,
):
    contract = require_runtime_accounting_contract(
        asset_id
    )

    assert contract.native_notional(
        quantity=quantity,
        price=price,
    ) == expected


def test_native_notional_uses_decimal_string_boundary():
    contract = require_runtime_accounting_contract(
        "BTCUSDT"
    )

    result = contract.native_notional(
        quantity=0.1,
        price=0.2,
    )

    assert result == Decimal("0.02")


@pytest.mark.parametrize(
    "asset_id",
    [
        "GOLD_FUT_CONT",
        "WTI_FUT_CONT",
    ],
)
def test_continuous_futures_proxies_are_fail_closed(asset_id):
    contract = get_instrument_accounting_contract(
        asset_id
    )

    assert contract.status is AccountingContractStatus.BLOCKED
    assert contract.runtime_accounting_ready is False
    assert contract.pnl_multiplier is None
    assert (
        "CONTINUOUS_FUTURE_PROXY"
        in contract.limitations
    )
    assert (
        "FUTURES_RUNTIME_QUANTITY_SEMANTICS_UNVERIFIED"
        in contract.limitations
    )
    assert (
        "FUTURES_FEE_MODEL_NOT_CONTRACT_AWARE"
        in contract.limitations
    )

    with pytest.raises(
        InstrumentAccountingContractError,
        match="ACCOUNTING_CONTRACT_BLOCKED",
    ):
        require_runtime_accounting_contract(
            asset_id
        )


def test_gold_reference_contract_is_documented_but_not_activated():
    contract = get_instrument_accounting_contract(
        "GOLD_FUT_CONT"
    )

    assert contract.reference_product_code == "GC"
    assert (
        contract.reference_contract_multiplier
        == Decimal("100")
    )
    assert contract.reference_contract_unit == "troy ounces"
    assert contract.reference_source == "CME_GROUP"
    assert contract.pnl_multiplier is None


def test_wti_reference_contract_is_documented_but_not_activated():
    contract = get_instrument_accounting_contract(
        "WTI_FUT_CONT"
    )

    assert contract.reference_product_code == "CL"
    assert (
        contract.reference_contract_multiplier
        == Decimal("1000")
    )
    assert contract.reference_contract_unit == "barrels"
    assert contract.reference_source == "CME_GROUP"
    assert contract.pnl_multiplier is None


@pytest.mark.parametrize(
    "asset_id",
    [
        "GOLD_FUT_CONT",
        "WTI_FUT_CONT",
    ],
)
def test_futures_reference_contract_matches_proxy_provider_symbol(
    asset_id,
):
    asset = get_asset(asset_id)
    contract = get_instrument_accounting_contract(
        asset_id
    )

    assert asset.instrument_type == "continuous_future_proxy"
    assert contract.instrument_type == "continuous_future_proxy"

    expected = {
        "GOLD_FUT_CONT": "GC=F",
        "WTI_FUT_CONT": "CL=F",
    }

    assert asset.provider_symbol == expected[asset_id]


@pytest.mark.parametrize(
    "asset_id",
    [
        "GOLD_FUT_CONT",
        "WTI_FUT_CONT",
    ],
)
def test_blocked_futures_notional_is_not_silently_computed(
    asset_id,
):
    contract = get_instrument_accounting_contract(
        asset_id
    )

    with pytest.raises(
        InstrumentAccountingContractError,
        match="ACCOUNTING_CONTRACT_BLOCKED",
    ):
        contract.native_notional(
            quantity="1",
            price="100",
        )


def test_unknown_asset_fails_closed():
    with pytest.raises(
        InstrumentAccountingContractError,
        match="UNKNOWN_ACCOUNTING_ASSET",
    ):
        get_instrument_accounting_contract(
            "DOES_NOT_EXIST"
        )


def test_contract_is_immutable():
    contract = get_instrument_accounting_contract(
        "BTCUSDT"
    )

    with pytest.raises(FrozenInstanceError):
        contract.asset_id = "CHANGED"


def test_ready_contract_rejects_nonpositive_notional_inputs():
    contract = require_runtime_accounting_contract(
        "AAPL"
    )

    with pytest.raises(
        InstrumentAccountingContractError
    ):
        contract.native_notional(
            quantity="0",
            price="100",
        )

    with pytest.raises(
        InstrumentAccountingContractError
    ):
        contract.native_notional(
            quantity="1",
            price="0",
        )


def test_accounting_readiness_is_not_paper_readiness():
    contract = get_instrument_accounting_contract(
        "AAPL"
    )

    assert contract.runtime_accounting_ready is True
    assert contract.paper_readiness is None