from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import Enum

from src.data.market_data import ExecutionQuality
from src.execution.models import OrderSide
from src.fx.models import FxFreshness


CAPITAL_EXPOSURE_FX_FRESH_REQUIRED = (
    "CAPITAL_EXPOSURE_FX_FRESH_REQUIRED"
)


class CapitalExposureReason(
    str,
    Enum,
):
    AVAILABLE = "AVAILABLE"
    ASSET_NOT_SUPPORTED = (
        "ASSET_NOT_SUPPORTED"
    )
    EXECUTION_QUALITY_NOT_SUPPORTED = (
        "EXECUTION_QUALITY_NOT_SUPPORTED"
    )
    QUANTITY_INVALID = (
        "QUANTITY_INVALID"
    )
    REFERENCE_PRICE_INVALID = (
        "REFERENCE_PRICE_INVALID"
    )
    SLIPPAGE_UNAVAILABLE = (
        "SLIPPAGE_UNAVAILABLE"
    )
    FX_UNAVAILABLE = (
        "FX_UNAVAILABLE"
    )
    FX_NOT_FRESH = (
        "FX_NOT_FRESH"
    )
    FX_PATH_INVALID = (
        "FX_PATH_INVALID"
    )
    EXPOSURE_INVALID = (
        "EXPOSURE_INVALID"
    )


@dataclass(frozen=True)
class ProposedLongExposure:
    available: bool
    reason: CapitalExposureReason

    asset_id: str
    quantity: Decimal | None

    reference_price: Decimal | None
    proposed_execution_price: Decimal | None

    native_notional: Decimal | None
    native_currency: str

    exposure_pln: Decimal | None

    fx_path: str | None
    fx_freshness: FxFreshness | None
    fx_quote_age_seconds: Decimal | None

    unavailable_detail: str | None
    limitations: tuple[str, ...]


def _decimal_or_none(
    value,
):
    if value is None:
        return None

    try:
        result = Decimal(
            str(value)
        )
    except (
        InvalidOperation,
        TypeError,
        ValueError,
    ):
        return None

    if not result.is_finite():
        return None

    return result


class BtcUsdtLongExposureCalculator:
    """
    Pure controlled BTCUSDT proposed-LONG-exposure calculator.

    Execution-price prediction matches the current REAL_BOOK BUY path:
    reference price = ASK
    proposed execution price = existing slippage model applied to ASK

    Gross native notional:
    proposed execution price * quantity

    PLN conversion:
    USDT -> USD -> PLN through the existing CurrencyConverter.

    No implicit USDT == USD is permitted.

    Capital admission requires reliable FX. For this controlled Phase 12
    path, only FX_FRESH is accepted. FX_STALE is fail-closed.

    This class does not read cash, enforce the capital limit, mutate
    PaperBroker/runtime state, reserve capital, model margin/collateral,
    or persist anything.
    """

    def __init__(
        self,
        *,
        slippage_model,
        fx_converter,
    ):
        apply = getattr(
            slippage_model,
            "apply",
            None,
        )

        convert = getattr(
            fx_converter,
            "convert_to_pln",
            None,
        )

        if not callable(apply):
            raise TypeError(
                "slippage_model.apply is required"
            )

        if not callable(convert):
            raise TypeError(
                "fx_converter.convert_to_pln is required"
            )

        self.slippage_model = (
            slippage_model
        )
        self.fx_converter = (
            fx_converter
        )

    @staticmethod
    def _unavailable(
        *,
        reason,
        asset_id,
        quantity=None,
        reference_price=None,
        proposed_execution_price=None,
        native_notional=None,
        fx_path=None,
        fx_freshness=None,
        fx_quote_age_seconds=None,
        detail=None,
        limitations=(),
    ):
        return ProposedLongExposure(
            available=False,
            reason=reason,
            asset_id=str(
                asset_id
            ),
            quantity=quantity,
            reference_price=(
                reference_price
            ),
            proposed_execution_price=(
                proposed_execution_price
            ),
            native_notional=(
                native_notional
            ),
            native_currency="USDT",
            exposure_pln=None,
            fx_path=fx_path,
            fx_freshness=(
                fx_freshness
            ),
            fx_quote_age_seconds=(
                fx_quote_age_seconds
            ),
            unavailable_detail=detail,
            limitations=tuple(
                limitations
            ),
        )

    def calculate(
        self,
        *,
        market_snapshot,
        quantity,
        fx_quotes,
    ):
        asset_id = str(
            getattr(
                market_snapshot,
                "asset_id",
                "",
            )
        ).strip()

        if asset_id != "BTCUSDT":
            return self._unavailable(
                reason=(
                    CapitalExposureReason
                    .ASSET_NOT_SUPPORTED
                ),
                asset_id=asset_id,
                detail=(
                    "CONTROLLED_BTCUSDT_ONLY"
                ),
            )

        quantity_decimal = (
            _decimal_or_none(
                quantity
            )
        )

        if (
            quantity_decimal is None
            or quantity_decimal <= 0
        ):
            return self._unavailable(
                reason=(
                    CapitalExposureReason
                    .QUANTITY_INVALID
                ),
                asset_id=asset_id,
                quantity=(
                    quantity_decimal
                ),
            )

        execution_quality = getattr(
            market_snapshot,
            "execution_quality",
            None,
        )

        if (
            execution_quality
            is not ExecutionQuality.REAL_BOOK
        ):
            return self._unavailable(
                reason=(
                    CapitalExposureReason
                    .EXECUTION_QUALITY_NOT_SUPPORTED
                ),
                asset_id=asset_id,
                quantity=(
                    quantity_decimal
                ),
                detail=str(
                    getattr(
                        execution_quality,
                        "value",
                        execution_quality,
                    )
                ),
            )

        reference_price = (
            _decimal_or_none(
                getattr(
                    market_snapshot,
                    "ask",
                    None,
                )
            )
        )

        if (
            reference_price is None
            or reference_price <= 0
        ):
            return self._unavailable(
                reason=(
                    CapitalExposureReason
                    .REFERENCE_PRICE_INVALID
                ),
                asset_id=asset_id,
                quantity=(
                    quantity_decimal
                ),
                reference_price=(
                    reference_price
                ),
            )

        try:
            proposed_execution_float = (
                self.slippage_model.apply(
                    float(
                        reference_price
                    ),
                    OrderSide.BUY,
                )
            )
        except Exception as exc:
            return self._unavailable(
                reason=(
                    CapitalExposureReason
                    .SLIPPAGE_UNAVAILABLE
                ),
                asset_id=asset_id,
                quantity=(
                    quantity_decimal
                ),
                reference_price=(
                    reference_price
                ),
                detail=(
                    f"{type(exc).__name__}: {exc}"
                ),
            )

        proposed_execution_price = (
            _decimal_or_none(
                proposed_execution_float
            )
        )

        if (
            proposed_execution_price is None
            or proposed_execution_price <= 0
        ):
            return self._unavailable(
                reason=(
                    CapitalExposureReason
                    .SLIPPAGE_UNAVAILABLE
                ),
                asset_id=asset_id,
                quantity=(
                    quantity_decimal
                ),
                reference_price=(
                    reference_price
                ),
                proposed_execution_price=(
                    proposed_execution_price
                ),
                detail=(
                    "INVALID_PROPOSED_EXECUTION_PRICE"
                ),
            )

        native_notional = (
            proposed_execution_price
            * quantity_decimal
        )

        try:
            conversion = (
                self.fx_converter
                .convert_to_pln(
                    float(
                        native_notional
                    ),
                    "USDT",
                    tuple(
                        fx_quotes
                    ),
                )
            )
        except Exception as exc:
            return self._unavailable(
                reason=(
                    CapitalExposureReason
                    .FX_UNAVAILABLE
                ),
                asset_id=asset_id,
                quantity=(
                    quantity_decimal
                ),
                reference_price=(
                    reference_price
                ),
                proposed_execution_price=(
                    proposed_execution_price
                ),
                native_notional=(
                    native_notional
                ),
                detail=(
                    f"{type(exc).__name__}: {exc}"
                ),
            )

        fx_path = getattr(
            getattr(
                conversion,
                "fx_path",
                None,
            ),
            "text",
            None,
        )

        fx_freshness = getattr(
            conversion,
            "freshness",
            None,
        )

        age_decimal = (
            _decimal_or_none(
                getattr(
                    conversion,
                    "quote_age_seconds",
                    None,
                )
            )
        )

        limitations = tuple(
            getattr(
                conversion,
                "limitations",
                (),
            )
        )

        if fx_path != "USDT→USD→PLN":
            return self._unavailable(
                reason=(
                    CapitalExposureReason
                    .FX_PATH_INVALID
                ),
                asset_id=asset_id,
                quantity=(
                    quantity_decimal
                ),
                reference_price=(
                    reference_price
                ),
                proposed_execution_price=(
                    proposed_execution_price
                ),
                native_notional=(
                    native_notional
                ),
                fx_path=fx_path,
                fx_freshness=(
                    fx_freshness
                ),
                fx_quote_age_seconds=(
                    age_decimal
                ),
                detail=(
                    "EXPECTED_USDT_USD_PLN"
                ),
                limitations=limitations,
            )

        if not bool(
            getattr(
                conversion,
                "available",
                False,
            )
        ):
            return self._unavailable(
                reason=(
                    CapitalExposureReason
                    .FX_UNAVAILABLE
                ),
                asset_id=asset_id,
                quantity=(
                    quantity_decimal
                ),
                reference_price=(
                    reference_price
                ),
                proposed_execution_price=(
                    proposed_execution_price
                ),
                native_notional=(
                    native_notional
                ),
                fx_path=fx_path,
                fx_freshness=(
                    fx_freshness
                ),
                fx_quote_age_seconds=(
                    age_decimal
                ),
                detail=(
                    getattr(
                        conversion,
                        "unavailable_reason",
                        None,
                    )
                ),
                limitations=limitations,
            )

        if (
            fx_freshness
            is not FxFreshness.FX_FRESH
        ):
            return self._unavailable(
                reason=(
                    CapitalExposureReason
                    .FX_NOT_FRESH
                ),
                asset_id=asset_id,
                quantity=(
                    quantity_decimal
                ),
                reference_price=(
                    reference_price
                ),
                proposed_execution_price=(
                    proposed_execution_price
                ),
                native_notional=(
                    native_notional
                ),
                fx_path=fx_path,
                fx_freshness=(
                    fx_freshness
                ),
                fx_quote_age_seconds=(
                    age_decimal
                ),
                detail=(
                    str(
                        getattr(
                            fx_freshness,
                            "value",
                            fx_freshness,
                        )
                    )
                ),
                limitations=(
                    *limitations,
                    CAPITAL_EXPOSURE_FX_FRESH_REQUIRED,
                ),
            )

        exposure_pln = (
            _decimal_or_none(
                getattr(
                    conversion,
                    "converted_amount",
                    None,
                )
            )
        )

        if (
            exposure_pln is None
            or exposure_pln <= 0
        ):
            return self._unavailable(
                reason=(
                    CapitalExposureReason
                    .EXPOSURE_INVALID
                ),
                asset_id=asset_id,
                quantity=(
                    quantity_decimal
                ),
                reference_price=(
                    reference_price
                ),
                proposed_execution_price=(
                    proposed_execution_price
                ),
                native_notional=(
                    native_notional
                ),
                fx_path=fx_path,
                fx_freshness=(
                    fx_freshness
                ),
                fx_quote_age_seconds=(
                    age_decimal
                ),
                detail=(
                    "INVALID_CONVERTED_EXPOSURE"
                ),
                limitations=limitations,
            )

        return ProposedLongExposure(
            available=True,
            reason=(
                CapitalExposureReason
                .AVAILABLE
            ),
            asset_id=asset_id,
            quantity=(
                quantity_decimal
            ),
            reference_price=(
                reference_price
            ),
            proposed_execution_price=(
                proposed_execution_price
            ),
            native_notional=(
                native_notional
            ),
            native_currency="USDT",
            exposure_pln=(
                exposure_pln
            ),
            fx_path=fx_path,
            fx_freshness=(
                fx_freshness
            ),
            fx_quote_age_seconds=(
                age_decimal
            ),
            unavailable_detail=None,
            limitations=limitations,
        )
