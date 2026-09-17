from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from src.fx.models import FxFreshness


MTM_EXIT_SLIPPAGE_LIMITATION = (
    "MTM_EXIT_SLIPPAGE_NOT_MODELLED"
)


class PlnMtmError(ValueError):
    pass


def _required_text(value, field_name):
    result = str(value).strip()

    if not result:
        raise PlnMtmError(
            f"{field_name} is required"
        )

    return result


def _decimal(value, field_name):
    try:
        result = Decimal(str(value))
    except (
        InvalidOperation,
        TypeError,
        ValueError,
    ) as exc:
        raise PlnMtmError(
            f"{field_name} must be a finite decimal"
        ) from exc

    if not result.is_finite():
        raise PlnMtmError(
            f"{field_name} must be a finite decimal"
        )

    return result


def _positive_decimal(value, field_name):
    result = _decimal(value, field_name)

    if result <= 0:
        raise PlnMtmError(
            f"{field_name} must be positive"
        )

    return result


def _nonnegative_decimal(value, field_name):
    result = _decimal(value, field_name)

    if result < 0:
        raise PlnMtmError(
            f"{field_name} cannot be negative"
        )

    return result


def _freshness(value):
    if isinstance(value, FxFreshness):
        return value

    try:
        return FxFreshness(str(value))
    except (TypeError, ValueError) as exc:
        raise PlnMtmError(
            "invalid fx_freshness"
        ) from exc


@dataclass(frozen=True)
class UnrealizedPlnMtmRecord:
    accounting_id: str
    asset_id: str
    position_id: str

    side: str
    native_currency: str

    quantity: Decimal
    pnl_multiplier: Decimal
    entry_price: Decimal

    bid: Decimal
    ask: Decimal
    mark_price: Decimal
    mark_source: str

    unrealized_pnl_native: Decimal
    estimated_exit_fee_native: Decimal
    estimated_net_liquidation_pnl_native: Decimal

    fx_freshness: FxFreshness
    fx_quote_age_seconds: Decimal | None
    fx_rate: Decimal | None
    fx_path: str

    unrealized_pnl_pln: Decimal | None
    estimated_exit_fee_pln: Decimal | None
    estimated_net_liquidation_pnl_pln: Decimal | None

    pln_available: bool
    unavailable_reason: str | None

    limitations: tuple[str, ...]


class PlnUnrealizedMtmKernel:
    """
    Pure deterministic unrealized-PnL / MTM kernel.

    Market mark:
        LONG  -> BID
        SHORT -> ASK

    This is liquidation-side marking against the visible/derived book.
    No midpoint substitution is performed.

    Unrealized PnL is price MTM only. An explicitly supplied estimated
    exit fee is exposed separately, together with an estimated net
    liquidation PnL. A.8 deliberately does not silently redefine
    unrealized PnL as fee-adjusted liquidation PnL.

    Exit slippage is not applied here. It remains an explicit limitation
    until a later integration layer supplies an execution-model estimate.

    Financial arithmetic crosses the boundary through Decimal(str(value)).
    No implicit rounding or quantization is applied.

    FX:
        FX_FRESH       -> PLN available
        FX_STALE       -> PLN available with explicit age
        FX_UNAVAILABLE -> native values remain available; PLN is None

    The kernel does not select FX providers, mutate runtime state,
    update cash/equity/exposure, persist a ledger, or introduce SQLite.
    """

    def calculate(
        self,
        *,
        accounting_id,
        asset_id,
        position_id,
        side,
        native_currency,
        quantity,
        entry_price,
        bid,
        ask,
        pnl_multiplier,
        estimated_exit_fee_native,
        fx_freshness,
        fx_rate,
        fx_path,
        fx_quote_age_seconds=None,
        fx_unavailable_reason=None,
    ):
        accounting_id = _required_text(
            accounting_id,
            "accounting_id",
        )

        asset_id = _required_text(
            asset_id,
            "asset_id",
        )

        position_id = _required_text(
            position_id,
            "position_id",
        )

        side = _required_text(
            side,
            "side",
        ).upper()

        if side not in {"LONG", "SHORT"}:
            raise PlnMtmError(
                "side must be LONG or SHORT"
            )

        native_currency = _required_text(
            native_currency,
            "native_currency",
        ).upper()

        quantity = _positive_decimal(
            quantity,
            "quantity",
        )

        entry_price = _positive_decimal(
            entry_price,
            "entry_price",
        )

        bid = _positive_decimal(
            bid,
            "bid",
        )

        ask = _positive_decimal(
            ask,
            "ask",
        )

        if bid > ask:
            raise PlnMtmError(
                "INVALID_BID_ASK"
            )

        multiplier = _positive_decimal(
            pnl_multiplier,
            "pnl_multiplier",
        )

        estimated_exit_fee_native = (
            _nonnegative_decimal(
                estimated_exit_fee_native,
                "estimated_exit_fee_native",
            )
        )

        if side == "LONG":
            mark_price = bid
            mark_source = "BID"
            direction = Decimal("1")
        else:
            mark_price = ask
            mark_source = "ASK"
            direction = Decimal("-1")

        unrealized_pnl_native = (
            (
                mark_price
                - entry_price
            )
            * quantity
            * multiplier
            * direction
        )

        estimated_net_liquidation_pnl_native = (
            unrealized_pnl_native
            - estimated_exit_fee_native
        )

        if native_currency == "PLN":
            freshness = FxFreshness.FX_FRESH
            age = Decimal("0")
            rate = Decimal("1")
            path = "PLN"
            unavailable_reason = None

            unrealized_pnl_pln = (
                unrealized_pnl_native
            )
            estimated_exit_fee_pln = (
                estimated_exit_fee_native
            )
            estimated_net_liquidation_pnl_pln = (
                estimated_net_liquidation_pnl_native
            )

            pln_available = True

        else:
            freshness = _freshness(
                fx_freshness
            )

            path = _required_text(
                fx_path,
                "fx_path",
            )

            if fx_quote_age_seconds is None:
                age = None
            else:
                age = _nonnegative_decimal(
                    fx_quote_age_seconds,
                    "fx_quote_age_seconds",
                )

            if (
                freshness
                is FxFreshness.FX_STALE
                and age is None
            ):
                raise PlnMtmError(
                    "STALE_FX_REQUIRES_AGE"
                )

            if (
                freshness
                is FxFreshness.FX_UNAVAILABLE
            ):
                if fx_rate is not None:
                    raise PlnMtmError(
                        "FX_UNAVAILABLE_RATE_MUST_BE_NONE"
                    )

                unavailable_reason = (
                    None
                    if fx_unavailable_reason is None
                    else str(
                        fx_unavailable_reason
                    ).strip()
                )

                if not unavailable_reason:
                    raise PlnMtmError(
                        "FX_UNAVAILABLE_REASON_REQUIRED"
                    )

                rate = None
                unrealized_pnl_pln = None
                estimated_exit_fee_pln = None
                estimated_net_liquidation_pnl_pln = None
                pln_available = False

            else:
                rate = _positive_decimal(
                    fx_rate,
                    "fx_rate",
                )

                unavailable_reason = None

                unrealized_pnl_pln = (
                    unrealized_pnl_native
                    * rate
                )

                estimated_exit_fee_pln = (
                    estimated_exit_fee_native
                    * rate
                )

                estimated_net_liquidation_pnl_pln = (
                    estimated_net_liquidation_pnl_native
                    * rate
                )

                pln_available = True

        return UnrealizedPlnMtmRecord(
            accounting_id=accounting_id,
            asset_id=asset_id,
            position_id=position_id,
            side=side,
            native_currency=native_currency,
            quantity=quantity,
            pnl_multiplier=multiplier,
            entry_price=entry_price,
            bid=bid,
            ask=ask,
            mark_price=mark_price,
            mark_source=mark_source,
            unrealized_pnl_native=(
                unrealized_pnl_native
            ),
            estimated_exit_fee_native=(
                estimated_exit_fee_native
            ),
            estimated_net_liquidation_pnl_native=(
                estimated_net_liquidation_pnl_native
            ),
            fx_freshness=freshness,
            fx_quote_age_seconds=age,
            fx_rate=rate,
            fx_path=path,
            unrealized_pnl_pln=(
                unrealized_pnl_pln
            ),
            estimated_exit_fee_pln=(
                estimated_exit_fee_pln
            ),
            estimated_net_liquidation_pnl_pln=(
                estimated_net_liquidation_pnl_pln
            ),
            pln_available=pln_available,
            unavailable_reason=(
                unavailable_reason
            ),
            limitations=(
                MTM_EXIT_SLIPPAGE_LIMITATION,
            ),
        )