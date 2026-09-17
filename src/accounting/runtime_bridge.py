from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from src.accounting.instrument_contracts import (
    require_runtime_accounting_contract,
)
from src.accounting.mtm_kernel import (
    PlnUnrealizedMtmKernel,
)
from src.accounting.pln_kernel import (
    PlnRealizedAccountingKernel,
)
from src.accounting.portfolio_snapshot import (
    PlnPortfolioSnapshotKernel,
)
from src.fx.models import FxFreshness


ACCOUNTING_PERSISTENCE_LIMITATION = (
    "ACCOUNTING_PERSISTENCE_NOT_IMPLEMENTED"
)

FULL_ENTRY_EXECUTION_REQUIREMENT = (
    "REALIZED_REQUIRES_FULL_ENTRY_EXECUTION"
)

_ARROW = "\u2192"

_CANONICAL_FX_PATHS = {
    "USD": f"USD{_ARROW}PLN",
    "EUR": f"EUR{_ARROW}PLN",
    "USDT": f"USDT{_ARROW}USD{_ARROW}PLN",
}


class RuntimeAccountingBridgeError(ValueError):
    pass


def _required_text(value, field_name):
    if value is None:
        raise RuntimeAccountingBridgeError(
            f"{field_name} is required"
        )

    result = str(value).strip()

    if not result:
        raise RuntimeAccountingBridgeError(
            f"{field_name} is required"
        )

    return result


def _decimal(value, field_name, *, positive=False):
    try:
        result = Decimal(str(value))
    except (
        InvalidOperation,
        TypeError,
        ValueError,
    ) as exc:
        raise RuntimeAccountingBridgeError(
            f"{field_name} must be a finite decimal"
        ) from exc

    if not result.is_finite():
        raise RuntimeAccountingBridgeError(
            f"{field_name} must be a finite decimal"
        )

    if positive and result <= 0:
        raise RuntimeAccountingBridgeError(
            f"{field_name} must be positive"
        )

    return result


def _side_name(value):
    raw = getattr(
        value,
        "value",
        value,
    )

    side = (
        str(raw)
        .strip()
        .upper()
    )

    if side not in {
        "LONG",
        "SHORT",
    }:
        raise RuntimeAccountingBridgeError(
            "POSITION_SIDE_UNSUPPORTED:"
            + side
        )

    return side


def _require_attr(obj, field_name):
    if obj is None:
        raise RuntimeAccountingBridgeError(
            f"{field_name} object is required"
        )

    if not hasattr(
        obj,
        field_name,
    ):
        raise RuntimeAccountingBridgeError(
            "MISSING_RUNTIME_FIELD:"
            + field_name
        )

    return getattr(
        obj,
        field_name,
    )


def _canonical_path(currency):
    normalized = (
        str(currency)
        .strip()
        .upper()
    )

    if normalized == "PLN":
        return "PLN"

    try:
        return _CANONICAL_FX_PATHS[
            normalized
        ]
    except KeyError as exc:
        raise RuntimeAccountingBridgeError(
            "NO_RUNTIME_FX_PATH:"
            + normalized
            + _ARROW
            + "PLN"
        ) from exc


@dataclass(frozen=True)
class RuntimeRealizedAccountingResult:
    accounting_record: object
    fx_booking: object
    limitations: tuple[str, ...]


class Phase09RuntimeAccountingBridge:
    """
    Fail-closed adapter between verified REALISTIC_V2 runtime objects
    and the isolated Phase 09 accounting kernels.

    This bridge performs no network I/O and no persistence.
    """

    def __init__(
        self,
        *,
        fx_enabled,
        pln_accounting_enabled,
        realized_fx_selection_policy=None,
        realized_fx_booker=None,
    ):
        if not isinstance(
            fx_enabled,
            bool,
        ):
            raise TypeError(
                "fx_enabled must be bool"
            )

        if not isinstance(
            pln_accounting_enabled,
            bool,
        ):
            raise TypeError(
                "pln_accounting_enabled must be bool"
            )

        self.fx_enabled = fx_enabled
        self.pln_accounting_enabled = (
            pln_accounting_enabled
        )

        self.realized_fx_selection_policy = (
            realized_fx_selection_policy
        )

        self.realized_fx_booker = (
            realized_fx_booker
        )

        self.mtm_kernel = (
            PlnUnrealizedMtmKernel()
        )

        self.realized_kernel = (
            PlnRealizedAccountingKernel()
        )

        self.portfolio_kernel = (
            PlnPortfolioSnapshotKernel()
        )

    def _require_pln_enabled(self):
        if not self.pln_accounting_enabled:
            raise RuntimeAccountingBridgeError(
                "PLN_ACCOUNTING_DISABLED"
            )

    def _require_fx_enabled(
        self,
        native_currency,
    ):
        if (
            str(native_currency)
            .strip()
            .upper()
            != "PLN"
            and not self.fx_enabled
        ):
            raise RuntimeAccountingBridgeError(
                "FX_ACCOUNTING_DISABLED"
            )

    def _contract_for(
        self,
        asset_id,
    ):
        return (
            require_runtime_accounting_contract(
                asset_id
            )
        )

    def _validate_position_asset(
        self,
        position,
    ):
        return _required_text(
            _require_attr(
                position,
                "asset_id",
            ),
            "position.asset_id",
        ).upper()

    def _mtm_fx_inputs(
        self,
        *,
        native_currency,
        fx_conversion,
    ):
        currency = (
            str(native_currency)
            .strip()
            .upper()
        )

        if currency == "PLN":
            if fx_conversion is not None:
                raise RuntimeAccountingBridgeError(
                    "PLN_NATIVE_MUST_NOT_USE_EXTERNAL_FX"
                )

            return {
                "fx_freshness": None,
                "fx_rate": None,
                "fx_path": None,
                "fx_quote_age_seconds": None,
                "fx_unavailable_reason": None,
            }

        self._require_fx_enabled(
            currency
        )

        if fx_conversion is None:
            raise RuntimeAccountingBridgeError(
                "FX_CONVERSION_REQUIRED:"
                + currency
            )

        source_currency = (
            _required_text(
                _require_attr(
                    fx_conversion,
                    "source_currency",
                ),
                "fx_conversion.source_currency",
            )
            .upper()
        )

        if source_currency != currency:
            raise RuntimeAccountingBridgeError(
                "FX_SOURCE_CURRENCY_MISMATCH:"
                + source_currency
                + ":"
                + currency
            )

        target_currency = (
            _required_text(
                _require_attr(
                    fx_conversion,
                    "target_currency",
                ),
                "fx_conversion.target_currency",
            )
            .upper()
        )

        if target_currency != "PLN":
            raise RuntimeAccountingBridgeError(
                "FX_TARGET_MUST_BE_PLN"
            )

        source_amount = _decimal(
            _require_attr(
                fx_conversion,
                "source_amount",
            ),
            "fx_conversion.source_amount",
        )

        if source_amount != Decimal("1"):
            raise RuntimeAccountingBridgeError(
                "FX_CONVERSION_MUST_BE_UNIT_RATE"
            )

        path = _require_attr(
            fx_conversion,
            "fx_path",
        )

        path_text = _required_text(
            getattr(
                path,
                "text",
                path,
            ),
            "fx_conversion.fx_path",
        )

        expected_path = _canonical_path(
            currency
        )

        if path_text != expected_path:
            raise RuntimeAccountingBridgeError(
                "FX_PATH_MISMATCH:"
                + path_text
                + ":"
                + expected_path
            )

        freshness = _require_attr(
            fx_conversion,
            "freshness",
        )

        if not isinstance(
            freshness,
            FxFreshness,
        ):
            try:
                freshness = FxFreshness(
                    str(freshness)
                )
            except ValueError as exc:
                raise RuntimeAccountingBridgeError(
                    "INVALID_FX_FRESHNESS"
                ) from exc

        rate = _require_attr(
            fx_conversion,
            "converted_amount",
        )

        age = getattr(
            fx_conversion,
            "quote_age_seconds",
            None,
        )

        unavailable_reason = getattr(
            fx_conversion,
            "unavailable_reason",
            None,
        )

        if (
            freshness
            is FxFreshness.FX_UNAVAILABLE
        ):
            if rate is not None:
                raise RuntimeAccountingBridgeError(
                    "FX_UNAVAILABLE_RATE_MUST_BE_NONE"
                )

            if not unavailable_reason:
                raise RuntimeAccountingBridgeError(
                    "FX_UNAVAILABLE_REASON_REQUIRED"
                )
        else:
            _decimal(
                rate,
                "fx_conversion.converted_amount",
                positive=True,
            )

        return {
            "fx_freshness": freshness,
            "fx_rate": rate,
            "fx_path": path_text,
            "fx_quote_age_seconds": age,
            "fx_unavailable_reason": (
                unavailable_reason
            ),
        }

    def mark_position(
        self,
        *,
        position,
        market_snapshot,
        fx_conversion,
        estimated_exit_fee_native,
        accounting_id=None,
    ):
        self._require_pln_enabled()

        asset_id = (
            self._validate_position_asset(
                position
            )
        )

        contract = self._contract_for(
            asset_id
        )

        snapshot_asset = (
            _required_text(
                _require_attr(
                    market_snapshot,
                    "asset_id",
                ),
                "market_snapshot.asset_id",
            )
            .upper()
        )

        if snapshot_asset != asset_id:
            raise RuntimeAccountingBridgeError(
                "MARKET_SNAPSHOT_ASSET_MISMATCH"
            )

        bid = _require_attr(
            market_snapshot,
            "bid",
        )

        ask = _require_attr(
            market_snapshot,
            "ask",
        )

        if (
            bid is None
            or ask is None
        ):
            raise RuntimeAccountingBridgeError(
                "MARKET_BOOK_REQUIRED"
            )

        fx_inputs = (
            self._mtm_fx_inputs(
                native_currency=(
                    contract.native_pnl_currency
                ),
                fx_conversion=(
                    fx_conversion
                ),
            )
        )

        position_id = _required_text(
            _require_attr(
                position,
                "position_id",
            ),
            "position.position_id",
        )

        if accounting_id is None:
            accounting_id = (
                "mtm:"
                + position_id
            )

        return self.mtm_kernel.calculate(
            accounting_id=(
                accounting_id
            ),
            asset_id=asset_id,
            position_id=position_id,
            side=_side_name(
                _require_attr(
                    position,
                    "side",
                )
            ),
            native_currency=(
                contract.native_pnl_currency
            ),
            quantity=_require_attr(
                position,
                "quantity",
            ),
            entry_price=_require_attr(
                position,
                "entry_price",
            ),
            bid=bid,
            ask=ask,
            pnl_multiplier=(
                contract.pnl_multiplier
            ),
            estimated_exit_fee_native=(
                estimated_exit_fee_native
            ),
            **fx_inputs,
        )

    def _validate_realized_executions(
        self,
        *,
        position,
        entry_execution,
        exit_execution,
    ):
        if entry_execution is None:
            raise RuntimeAccountingBridgeError(
                "ENTRY_EXECUTION_REQUIRED"
            )

        if exit_execution is None:
            raise RuntimeAccountingBridgeError(
                "EXIT_EXECUTION_REQUIRED"
            )

        position_asset = (
            self._validate_position_asset(
                position
            )
        )

        entry_asset = (
            _required_text(
                _require_attr(
                    entry_execution,
                    "asset_id",
                ),
                "entry_execution.asset_id",
            )
            .upper()
        )

        exit_asset = (
            _required_text(
                _require_attr(
                    exit_execution,
                    "asset_id",
                ),
                "exit_execution.asset_id",
            )
            .upper()
        )

        if (
            entry_asset != position_asset
            or exit_asset != position_asset
        ):
            raise RuntimeAccountingBridgeError(
                "REALIZED_EXECUTION_ASSET_MISMATCH"
            )

        expected_entry_id = (
            _required_text(
                _require_attr(
                    position,
                    "entry_execution_id",
                ),
                "position.entry_execution_id",
            )
        )

        actual_entry_id = (
            _required_text(
                _require_attr(
                    entry_execution,
                    "execution_id",
                ),
                "entry_execution.execution_id",
            )
        )

        if actual_entry_id != expected_entry_id:
            raise RuntimeAccountingBridgeError(
                "ENTRY_EXECUTION_MISMATCH"
            )

        actual_exit_id = (
            _required_text(
                _require_attr(
                    exit_execution,
                    "execution_id",
                ),
                "exit_execution.execution_id",
            )
        )

        expected_exit_id = getattr(
            position,
            "exit_execution_id",
            None,
        )

        if (
            expected_exit_id is not None
            and str(expected_exit_id).strip()
            and str(expected_exit_id).strip()
            != actual_exit_id
        ):
            raise RuntimeAccountingBridgeError(
                "EXIT_EXECUTION_MISMATCH"
            )

        closed_at = getattr(
            position,
            "closed_at",
            None,
        )

        if closed_at is None:
            raise RuntimeAccountingBridgeError(
                "POSITION_CLOSED_AT_REQUIRED"
            )

        return (
            position_asset,
            actual_exit_id,
            closed_at,
        )

    def book_realized(
        self,
        *,
        position,
        entry_execution,
        exit_execution,
        fx_quotes,
        accounting_id=None,
        booking_id=None,
    ):
        self._require_pln_enabled()

        (
            asset_id,
            exit_execution_id,
            closed_at,
        ) = self._validate_realized_executions(
            position=position,
            entry_execution=entry_execution,
            exit_execution=exit_execution,
        )

        contract = self._contract_for(
            asset_id
        )

        self._require_fx_enabled(
            contract.native_pnl_currency
        )

        if (
            self.realized_fx_selection_policy
            is None
        ):
            raise RuntimeAccountingBridgeError(
                "REALIZED_FX_SELECTION_POLICY_REQUIRED"
            )

        if self.realized_fx_booker is None:
            raise RuntimeAccountingBridgeError(
                "REALIZED_FX_BOOKER_REQUIRED"
            )

        position_id = _required_text(
            _require_attr(
                position,
                "position_id",
            ),
            "position.position_id",
        )

        side = _side_name(
            _require_attr(
                position,
                "side",
            )
        )

        if accounting_id is None:
            accounting_id = (
                "realized:"
                + position_id
                + ":"
                + exit_execution_id
            )

        if booking_id is None:
            booking_id = (
                "fx:"
                + position_id
                + ":"
                + exit_execution_id
            )

        native_probe = (
            self.realized_kernel.calculate(
                accounting_id=(
                    "native-probe:"
                    + position_id
                    + ":"
                    + exit_execution_id
                ),
                position_id=position_id,
                side=side,
                native_currency=(
                    contract.native_pnl_currency
                ),
                pnl_multiplier=(
                    contract.pnl_multiplier
                ),
                fx_rate=Decimal("1"),
                fx_path=_canonical_path(
                    contract.native_pnl_currency
                ),
                entry_execution=(
                    entry_execution
                ),
                exit_execution=(
                    exit_execution
                ),
            )
        )

        selected_quotes = (
            self.realized_fx_selection_policy
            .select(
                closed_at=closed_at,
                native_currency=(
                    contract.native_pnl_currency
                ),
                quotes=tuple(
                    fx_quotes
                ),
            )
        )

        fx_booking = (
            self.realized_fx_booker
            .book(
                booking_id=booking_id,
                asset_id=asset_id,
                close_execution_id=(
                    exit_execution_id
                ),
                closed_at=closed_at,
                native_pnl=float(
                    native_probe
                    .net_realized_pnl_native
                ),
                native_currency=(
                    contract.native_pnl_currency
                ),
                quotes=selected_quotes,
            )
        )

        accounting_record = (
            self.realized_kernel.calculate(
                accounting_id=accounting_id,
                position_id=position_id,
                side=side,
                native_currency=(
                    contract.native_pnl_currency
                ),
                pnl_multiplier=(
                    contract.pnl_multiplier
                ),
                fx_rate=(
                    fx_booking.fx_rate
                ),
                fx_path=(
                    fx_booking.fx_path
                ),
                entry_execution=(
                    entry_execution
                ),
                exit_execution=(
                    exit_execution
                ),
            )
        )

        if (
            accounting_record
            .net_realized_pnl_native
            != native_probe
            .net_realized_pnl_native
        ):
            raise RuntimeAccountingBridgeError(
                "REALIZED_NATIVE_PNL_DRIFT"
            )

        limitations = tuple(
            dict.fromkeys(
                tuple(
                    fx_booking.limitations
                )
                + (
                    ACCOUNTING_PERSISTENCE_LIMITATION,
                )
            )
        )

        return RuntimeRealizedAccountingResult(
            accounting_record=(
                accounting_record
            ),
            fx_booking=fx_booking,
            limitations=limitations,
        )

    def portfolio_snapshot(
        self,
        *,
        cash_pln,
        mtm_records,
    ):
        self._require_pln_enabled()

        return (
            self.portfolio_kernel
            .calculate(
                cash_pln=cash_pln,
                mtm_records=tuple(
                    mtm_records
                ),
            )
        )