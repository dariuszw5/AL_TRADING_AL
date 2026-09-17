from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import Enum
from types import MappingProxyType

from src.data.assets import get_asset


class InstrumentAccountingContractError(
    ValueError
):
    pass


class AccountingContractStatus(
    str,
    Enum,
):
    READY = "READY"
    BLOCKED = "BLOCKED"


class QuantitySemantics(
    str,
    Enum,
):
    BASE_UNITS = "BASE_UNITS"
    SHARES = "SHARES"
    FUTURES_CONTRACTS = "FUTURES_CONTRACTS"


def _positive_decimal(
    value,
    field_name,
):
    try:
        result = Decimal(
            str(value)
        )
    except (
        InvalidOperation,
        TypeError,
        ValueError,
    ) as exc:
        raise InstrumentAccountingContractError(
            f"{field_name} must be a finite decimal"
        ) from exc

    if (
        not result.is_finite()
        or result <= 0
    ):
        raise InstrumentAccountingContractError(
            f"{field_name} must be positive"
        )

    return result


@dataclass(frozen=True)
class InstrumentAccountingContract:
    asset_id: str
    instrument_type: str
    native_pnl_currency: str
    quantity_semantics: QuantitySemantics

    status: AccountingContractStatus
    pnl_multiplier: Decimal | None

    reference_product_code: str | None = None
    reference_contract_multiplier: Decimal | None = None
    reference_contract_unit: str | None = None
    reference_source: str | None = None
    reference_url: str | None = None

    limitations: tuple[str, ...] = ()
    paper_readiness: None = None

    def __post_init__(self):
        if not self.asset_id.strip():
            raise InstrumentAccountingContractError(
                "asset_id is required"
            )

        if not self.instrument_type.strip():
            raise InstrumentAccountingContractError(
                "instrument_type is required"
            )

        if not self.native_pnl_currency.strip():
            raise InstrumentAccountingContractError(
                "native_pnl_currency is required"
            )

        if (
            self.status
            is AccountingContractStatus.READY
        ):
            if self.pnl_multiplier is None:
                raise InstrumentAccountingContractError(
                    "READY contract requires pnl_multiplier"
                )

            if self.pnl_multiplier <= 0:
                raise InstrumentAccountingContractError(
                    "pnl_multiplier must be positive"
                )

        if (
            self.status
            is AccountingContractStatus.BLOCKED
            and self.pnl_multiplier is not None
        ):
            raise InstrumentAccountingContractError(
                "BLOCKED contract must not expose runtime pnl_multiplier"
            )

        if (
            self.reference_contract_multiplier
            is not None
            and self.reference_contract_multiplier <= 0
        ):
            raise InstrumentAccountingContractError(
                "reference_contract_multiplier must be positive"
            )

    @property
    def runtime_accounting_ready(
        self,
    ):
        return (
            self.status
            is AccountingContractStatus.READY
            and self.pnl_multiplier is not None
        )

    def native_notional(
        self,
        *,
        quantity,
        price,
    ):
        if not self.runtime_accounting_ready:
            raise InstrumentAccountingContractError(
                "ACCOUNTING_CONTRACT_BLOCKED:"
                + self.asset_id
            )

        quantity = _positive_decimal(
            quantity,
            "quantity",
        )

        price = _positive_decimal(
            price,
            "price",
        )

        return (
            quantity
            * price
            * self.pnl_multiplier
        )


def _ready(
    *,
    asset_id,
    instrument_type,
    native_pnl_currency,
    quantity_semantics,
):
    return InstrumentAccountingContract(
        asset_id=asset_id,
        instrument_type=instrument_type,
        native_pnl_currency=native_pnl_currency,
        quantity_semantics=quantity_semantics,
        status=AccountingContractStatus.READY,
        pnl_multiplier=Decimal("1"),
        limitations=(
            "ACCOUNTING_READY_DOES_NOT_IMPLY_PAPER_READY",
        ),
    )


_CONTRACTS = {
    "BTCUSDT": _ready(
        asset_id="BTCUSDT",
        instrument_type="spot_reference",
        native_pnl_currency="USDT",
        quantity_semantics=(
            QuantitySemantics.BASE_UNITS
        ),
    ),
    "ETHUSDT": _ready(
        asset_id="ETHUSDT",
        instrument_type="spot_reference",
        native_pnl_currency="USDT",
        quantity_semantics=(
            QuantitySemantics.BASE_UNITS
        ),
    ),
    "SOLUSDT": _ready(
        asset_id="SOLUSDT",
        instrument_type="spot_reference",
        native_pnl_currency="USDT",
        quantity_semantics=(
            QuantitySemantics.BASE_UNITS
        ),
    ),
    "BNBUSDT": _ready(
        asset_id="BNBUSDT",
        instrument_type="spot_reference",
        native_pnl_currency="USDT",
        quantity_semantics=(
            QuantitySemantics.BASE_UNITS
        ),
    ),
    "XRPUSDT": _ready(
        asset_id="XRPUSDT",
        instrument_type="spot_reference",
        native_pnl_currency="USDT",
        quantity_semantics=(
            QuantitySemantics.BASE_UNITS
        ),
    ),
    "EURUSD": _ready(
        asset_id="EURUSD",
        instrument_type="fx_spot_reference",
        native_pnl_currency="USD",
        quantity_semantics=(
            QuantitySemantics.BASE_UNITS
        ),
    ),
    "AAPL": _ready(
        asset_id="AAPL",
        instrument_type="equity_reference",
        native_pnl_currency="USD",
        quantity_semantics=(
            QuantitySemantics.SHARES
        ),
    ),

    # IMPORTANT:
    # The exchange reference multipliers below are documented facts for
    # the standard GC and CL contracts. They are deliberately NOT exposed
    # as runtime pnl_multiplier values.
    #
    # Why:
    # - these app instruments are continuous Yahoo futures proxies;
    # - current generic position sizing is price-unit based and has no
    #   contract multiplier;
    # - current PaperBroker fee math is price * quantity * fee_rate and
    #   is not a futures per-contract fee model;
    # - rollover remains unresolved.
    #
    # Activating 100/1000 as runtime multipliers without changing sizing
    # and fee semantics would create internally inconsistent accounting.
    "GOLD_FUT_CONT": InstrumentAccountingContract(
        asset_id="GOLD_FUT_CONT",
        instrument_type="continuous_future_proxy",
        native_pnl_currency="USD",
        quantity_semantics=(
            QuantitySemantics.FUTURES_CONTRACTS
        ),
        status=AccountingContractStatus.BLOCKED,
        pnl_multiplier=None,
        reference_product_code="GC",
        reference_contract_multiplier=Decimal("100"),
        reference_contract_unit="troy ounces",
        reference_source="CME_GROUP",
        reference_url=(
            "https://www.cmegroup.com/"
            "markets/metals/precious/gold-futures.html"
        ),
        limitations=(
            "CONTINUOUS_FUTURE_PROXY",
            "FUTURES_RUNTIME_QUANTITY_SEMANTICS_UNVERIFIED",
            "FUTURES_FEE_MODEL_NOT_CONTRACT_AWARE",
            "CONTINUOUS_FUTURE_ROLLOVER_UNRESOLVED",
        ),
    ),
    "WTI_FUT_CONT": InstrumentAccountingContract(
        asset_id="WTI_FUT_CONT",
        instrument_type="continuous_future_proxy",
        native_pnl_currency="USD",
        quantity_semantics=(
            QuantitySemantics.FUTURES_CONTRACTS
        ),
        status=AccountingContractStatus.BLOCKED,
        pnl_multiplier=None,
        reference_product_code="CL",
        reference_contract_multiplier=Decimal("1000"),
        reference_contract_unit="barrels",
        reference_source="CME_GROUP",
        reference_url=(
            "https://www.cmegroup.com/"
            "education/articles-and-reports/"
            "micro-wti-crude-oil-futures-faq"
        ),
        limitations=(
            "CONTINUOUS_FUTURE_PROXY",
            "FUTURES_RUNTIME_QUANTITY_SEMANTICS_UNVERIFIED",
            "FUTURES_FEE_MODEL_NOT_CONTRACT_AWARE",
            "CONTINUOUS_FUTURE_ROLLOVER_UNRESOLVED",
        ),
    ),
}


INSTRUMENT_ACCOUNTING_CONTRACTS = (
    MappingProxyType(
        _CONTRACTS
    )
)


def _validate_registry_identity(
    contract,
):
    asset = get_asset(
        contract.asset_id
    )

    if (
        asset.instrument_type
        != contract.instrument_type
    ):
        raise InstrumentAccountingContractError(
            "ASSET_INSTRUMENT_TYPE_DRIFT:"
            + contract.asset_id
        )

    if (
        asset.quote_currency.upper()
        != contract.native_pnl_currency.upper()
    ):
        raise InstrumentAccountingContractError(
            "ASSET_QUOTE_CURRENCY_DRIFT:"
            + contract.asset_id
        )

    return contract


def get_instrument_accounting_contract(
    asset_id,
):
    normalized = str(
        asset_id
    ).strip().upper()

    try:
        contract = (
            INSTRUMENT_ACCOUNTING_CONTRACTS[
                normalized
            ]
        )
    except KeyError as exc:
        raise InstrumentAccountingContractError(
            "UNKNOWN_ACCOUNTING_ASSET:"
            + normalized
        ) from exc

    return _validate_registry_identity(
        contract
    )


def require_runtime_accounting_contract(
    asset_id,
):
    contract = (
        get_instrument_accounting_contract(
            asset_id
        )
    )

    if not contract.runtime_accounting_ready:
        raise InstrumentAccountingContractError(
            "ACCOUNTING_CONTRACT_BLOCKED:"
            + contract.asset_id
        )

    return contract


def list_instrument_accounting_contracts():
    return tuple(
        get_instrument_accounting_contract(
            asset_id
        )
        for asset_id in sorted(
            INSTRUMENT_ACCOUNTING_CONTRACTS
        )
    )