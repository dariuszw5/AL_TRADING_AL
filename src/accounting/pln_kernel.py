from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


class PlnAccountingError(
    ValueError
):
    pass


def _required_text(
    value,
    field_name,
):
    result = str(
        value
    ).strip()

    if not result:
        raise PlnAccountingError(
            f"{field_name} is required"
        )

    return result


def _decimal(
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
        raise PlnAccountingError(
            f"{field_name} must be a finite decimal"
        ) from exc

    if not result.is_finite():
        raise PlnAccountingError(
            f"{field_name} must be a finite decimal"
        )

    return result


def _positive_decimal(
    value,
    field_name,
):
    result = _decimal(
        value,
        field_name,
    )

    if result <= 0:
        raise PlnAccountingError(
            f"{field_name} must be positive"
        )

    return result


def _nonnegative_decimal(
    value,
    field_name,
):
    result = _decimal(
        value,
        field_name,
    )

    if result < 0:
        raise PlnAccountingError(
            f"{field_name} cannot be negative"
        )

    return result


def _side_name(
    value,
):
    enum_value = getattr(
        value,
        "value",
        value,
    )

    return (
        str(enum_value)
        .strip()
        .upper()
    )


@dataclass(frozen=True)
class RealizedPlnAccountingRecord:
    accounting_id: str
    asset_id: str
    position_id: str
    entry_execution_id: str
    exit_execution_id: str

    side: str
    native_currency: str

    quantity: Decimal
    pnl_multiplier: Decimal

    entry_execution_price: Decimal
    exit_execution_price: Decimal

    price_pnl_native: Decimal
    fees_native: Decimal
    net_realized_pnl_native: Decimal

    spread_cost_native: Decimal
    slippage_cost_native: Decimal

    fx_rate: Decimal
    fx_path: str

    price_pnl_pln: Decimal
    fees_pln: Decimal
    net_realized_pnl_pln: Decimal

    spread_cost_pln: Decimal
    slippage_cost_pln: Decimal

    cost_attribution_only: bool = True


class PlnRealizedAccountingKernel:
    """
    Pure deterministic REALISTIC_V2 accounting kernel.

    Semantics:

    1. PnL uses ACTUAL execution prices.
       Those prices already include:
       - bid/ask side selection,
       - spread impact,
       - configured slippage.

    2. Execution.fee is a separate monetary amount.
       It is deducted exactly once.

    3. spread_cost and slippage_cost are attribution/reporting
       fields only. They must NOT be deducted again from PnL.

    4. Financial arithmetic crosses into Decimal via:
           Decimal(str(value))

    5. No implicit currency rounding is applied here.

    6. pnl_multiplier is mandatory. The kernel never assumes
       contract multiplier 1 for every instrument class.

    This module does not mutate cash, equity, positions,
    live_state or any ledger.
    """

    @staticmethod
    def _validate_execution(
        execution,
        label,
    ):
        required = (
            "execution_id",
            "asset_id",
            "side",
            "quantity",
            "execution_price",
            "bid",
            "ask",
            "slippage",
            "fee",
        )

        missing = [
            field
            for field in required
            if not hasattr(
                execution,
                field,
            )
        ]

        if missing:
            raise PlnAccountingError(
                f"{label} execution missing fields: "
                + ",".join(
                    missing
                )
            )

    @staticmethod
    def _validate_book(
        *,
        bid,
        ask,
        label,
    ):
        if (
            bid <= 0
            or ask <= 0
            or bid > ask
        ):
            raise PlnAccountingError(
                "INVALID_BID_ASK:"
                + label
            )

    def calculate(
        self,
        *,
        accounting_id,
        position_id,
        side,
        native_currency,
        pnl_multiplier,
        fx_rate,
        fx_path,
        entry_execution,
        exit_execution,
    ):
        accounting_id = _required_text(
            accounting_id,
            "accounting_id",
        )

        position_id = _required_text(
            position_id,
            "position_id",
        )

        native_currency = (
            _required_text(
                native_currency,
                "native_currency",
            )
            .upper()
        )

        fx_path = _required_text(
            fx_path,
            "fx_path",
        )

        side = (
            _required_text(
                side,
                "side",
            )
            .upper()
        )

        if side not in {
            "LONG",
            "SHORT",
        }:
            raise PlnAccountingError(
                "side must be LONG or SHORT"
            )

        multiplier = (
            _positive_decimal(
                pnl_multiplier,
                "pnl_multiplier",
            )
        )

        fx_rate = _positive_decimal(
            fx_rate,
            "fx_rate",
        )

        self._validate_execution(
            entry_execution,
            "entry",
        )

        self._validate_execution(
            exit_execution,
            "exit",
        )

        entry_asset = _required_text(
            entry_execution.asset_id,
            "entry asset_id",
        )

        exit_asset = _required_text(
            exit_execution.asset_id,
            "exit asset_id",
        )

        if entry_asset != exit_asset:
            raise PlnAccountingError(
                "EXECUTION_ASSET_MISMATCH"
            )

        quantity = _positive_decimal(
            entry_execution.quantity,
            "entry quantity",
        )

        exit_quantity = (
            _positive_decimal(
                exit_execution.quantity,
                "exit quantity",
            )
        )

        if quantity != exit_quantity:
            raise PlnAccountingError(
                "EXECUTION_QUANTITY_MISMATCH"
            )

        entry_side = _side_name(
            entry_execution.side
        )

        exit_side = _side_name(
            exit_execution.side
        )

        expected = (
            ("BUY", "SELL")
            if side == "LONG"
            else ("SELL", "BUY")
        )

        if (
            entry_side,
            exit_side,
        ) != expected:
            raise PlnAccountingError(
                "EXECUTION_SIDE_MISMATCH"
            )

        entry_price = _positive_decimal(
            entry_execution.execution_price,
            "entry execution_price",
        )

        exit_price = _positive_decimal(
            exit_execution.execution_price,
            "exit execution_price",
        )

        entry_bid = _positive_decimal(
            entry_execution.bid,
            "entry bid",
        )

        entry_ask = _positive_decimal(
            entry_execution.ask,
            "entry ask",
        )

        exit_bid = _positive_decimal(
            exit_execution.bid,
            "exit bid",
        )

        exit_ask = _positive_decimal(
            exit_execution.ask,
            "exit ask",
        )

        self._validate_book(
            bid=entry_bid,
            ask=entry_ask,
            label="ENTRY",
        )

        self._validate_book(
            bid=exit_bid,
            ask=exit_ask,
            label="EXIT",
        )

        entry_slippage = (
            _nonnegative_decimal(
                entry_execution.slippage,
                "entry slippage",
            )
        )

        exit_slippage = (
            _nonnegative_decimal(
                exit_execution.slippage,
                "exit slippage",
            )
        )

        entry_fee = _nonnegative_decimal(
            entry_execution.fee,
            "entry fee",
        )

        exit_fee = _nonnegative_decimal(
            exit_execution.fee,
            "exit fee",
        )

        direction = (
            Decimal("1")
            if side == "LONG"
            else Decimal("-1")
        )

        price_pnl_native = (
            (
                exit_price
                - entry_price
            )
            * quantity
            * multiplier
            * direction
        )

        fees_native = (
            entry_fee
            + exit_fee
        )

        net_realized_pnl_native = (
            price_pnl_native
            - fees_native
        )

        entry_half_spread = (
            entry_ask
            - entry_bid
        ) / Decimal("2")

        exit_half_spread = (
            exit_ask
            - exit_bid
        ) / Decimal("2")

        spread_cost_native = (
            (
                entry_half_spread
                + exit_half_spread
            )
            * quantity
            * multiplier
        )

        slippage_cost_native = (
            (
                entry_slippage
                + exit_slippage
            )
            * quantity
            * multiplier
        )

        price_pnl_pln = (
            price_pnl_native
            * fx_rate
        )

        fees_pln = (
            fees_native
            * fx_rate
        )

        net_realized_pnl_pln = (
            net_realized_pnl_native
            * fx_rate
        )

        spread_cost_pln = (
            spread_cost_native
            * fx_rate
        )

        slippage_cost_pln = (
            slippage_cost_native
            * fx_rate
        )

        if (
            price_pnl_native
            - fees_native
            != net_realized_pnl_native
        ):
            raise PlnAccountingError(
                "NATIVE_ACCOUNTING_INVARIANT_BROKEN"
            )

        if (
            price_pnl_pln
            - fees_pln
            != net_realized_pnl_pln
        ):
            raise PlnAccountingError(
                "PLN_ACCOUNTING_INVARIANT_BROKEN"
            )

        return RealizedPlnAccountingRecord(
            accounting_id=accounting_id,
            asset_id=entry_asset,
            position_id=position_id,
            entry_execution_id=(
                _required_text(
                    entry_execution.execution_id,
                    "entry execution_id",
                )
            ),
            exit_execution_id=(
                _required_text(
                    exit_execution.execution_id,
                    "exit execution_id",
                )
            ),
            side=side,
            native_currency=(
                native_currency
            ),
            quantity=quantity,
            pnl_multiplier=multiplier,
            entry_execution_price=(
                entry_price
            ),
            exit_execution_price=(
                exit_price
            ),
            price_pnl_native=(
                price_pnl_native
            ),
            fees_native=fees_native,
            net_realized_pnl_native=(
                net_realized_pnl_native
            ),
            spread_cost_native=(
                spread_cost_native
            ),
            slippage_cost_native=(
                slippage_cost_native
            ),
            fx_rate=fx_rate,
            fx_path=fx_path,
            price_pnl_pln=(
                price_pnl_pln
            ),
            fees_pln=fees_pln,
            net_realized_pnl_pln=(
                net_realized_pnl_pln
            ),
            spread_cost_pln=(
                spread_cost_pln
            ),
            slippage_cost_pln=(
                slippage_cost_pln
            ),
            cost_attribution_only=True,
        )
