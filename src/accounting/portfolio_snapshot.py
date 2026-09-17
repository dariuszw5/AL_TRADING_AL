from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from src.accounting.instrument_contracts import (
    InstrumentAccountingContractError,
    require_runtime_accounting_contract,
)
from src.fx.models import FxFreshness


class PlnPortfolioSnapshotError(
    ValueError
):
    pass


PORTFOLIO_CASH_CALLER_SUPPLIED = (
    "PORTFOLIO_CASH_IS_CALLER_SUPPLIED"
)

PORTFOLIO_FX_INCOMPLETE = (
    "PORTFOLIO_PLN_INCOMPLETE_DUE_TO_FX"
)


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
        raise PlnPortfolioSnapshotError(
            f"{field_name} must be a finite decimal"
        ) from exc

    if not result.is_finite():
        raise PlnPortfolioSnapshotError(
            f"{field_name} must be a finite decimal"
        )

    return result


def _required_decimal(
    value,
    field_name,
):
    if value is None:
        raise PlnPortfolioSnapshotError(
            f"{field_name} is required"
        )

    return _decimal(
        value,
        field_name,
    )


def _required_text(
    value,
    field_name,
):
    result = str(
        value
    ).strip()

    if not result:
        raise PlnPortfolioSnapshotError(
            f"{field_name} is required"
        )

    return result


def _freshness(
    value,
):
    if isinstance(
        value,
        FxFreshness,
    ):
        return value

    try:
        return FxFreshness(
            str(value)
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise PlnPortfolioSnapshotError(
            "invalid fx_freshness"
        ) from exc


@dataclass(frozen=True)
class PlnPortfolioSnapshot:
    cash_pln: Decimal
    position_count: int

    unrealized_pnl_pln: Decimal | None
    estimated_exit_fees_pln: Decimal | None
    estimated_net_liquidation_pnl_pln: Decimal | None

    equity_pln: Decimal | None
    estimated_liquidation_equity_pln: Decimal | None
    exposure_pln: Decimal | None

    pln_available: bool
    fx_freshness: FxFreshness
    max_fx_quote_age_seconds: Decimal | None

    stale_assets: tuple[str, ...]
    unavailable_assets: tuple[str, ...]
    limitations: tuple[str, ...]


class PlnPortfolioSnapshotKernel:
    """
    Pure deterministic portfolio-level PLN aggregation.

    IMPORTANT CASH CONTRACT

    `cash_pln` is caller-supplied settled PLN cash.

    A.10 does not reconstruct cash from realized trades and does not
    mutate a ledger. This avoids inventing booking order and avoids
    double-counting entry/exit fees before a runtime ledger policy exists.

    EQUITY CONTRACT

    equity_pln
        = cash_pln
        + sum(open-position unrealized_pnl_pln)

    estimated_liquidation_equity_pln
        = cash_pln
        + sum(open-position estimated_net_liquidation_pnl_pln)

    The two values stay separate because future exit fees are not yet
    incurred cash costs, while the liquidation estimate intentionally
    includes them.

    EXPOSURE CONTRACT

    exposure is current mark-side gross notional in PLN:

        quantity
        * mark_price
        * verified instrument pnl_multiplier
        * fx_rate

    This is gross market exposure, not margin requirement and not PnL.

    FX CONTRACT

    - all FRESH -> portfolio FRESH
    - any STALE and none unavailable -> portfolio STALE
    - any UNAVAILABLE -> portfolio PLN totals are unavailable

    A.10 never silently sums a partial portfolio when one position cannot
    be converted to PLN.

    This module does not mutate runtime state or persistence.
    """

    @staticmethod
    def _validate_record_shape(
        record,
    ):
        required = (
            "asset_id",
            "position_id",
            "native_currency",
            "quantity",
            "pnl_multiplier",
            "mark_price",
            "unrealized_pnl_pln",
            "estimated_exit_fee_pln",
            "estimated_net_liquidation_pnl_pln",
            "pln_available",
            "fx_freshness",
            "fx_quote_age_seconds",
            "fx_rate",
            "limitations",
        )

        missing = [
            field
            for field in required
            if not hasattr(
                record,
                field,
            )
        ]

        if missing:
            raise PlnPortfolioSnapshotError(
                "MTM_RECORD_MISSING_FIELDS:"
                + ",".join(
                    missing
                )
            )

    def calculate(
        self,
        *,
        cash_pln,
        mtm_records,
    ):
        cash = _decimal(
            cash_pln,
            "cash_pln",
        )

        records = tuple(
            mtm_records
        )

        if not records:
            return PlnPortfolioSnapshot(
                cash_pln=cash,
                position_count=0,
                unrealized_pnl_pln=Decimal("0"),
                estimated_exit_fees_pln=Decimal("0"),
                estimated_net_liquidation_pnl_pln=(
                    Decimal("0")
                ),
                equity_pln=cash,
                estimated_liquidation_equity_pln=(
                    cash
                ),
                exposure_pln=Decimal("0"),
                pln_available=True,
                fx_freshness=FxFreshness.FX_FRESH,
                max_fx_quote_age_seconds=(
                    Decimal("0")
                ),
                stale_assets=(),
                unavailable_assets=(),
                limitations=(
                    PORTFOLIO_CASH_CALLER_SUPPLIED,
                ),
            )

        seen_positions = set()

        stale_assets = set()
        unavailable_assets = set()
        ages = []
        limitations = {
            PORTFOLIO_CASH_CALLER_SUPPLIED,
        }

        total_unrealized = Decimal("0")
        total_exit_fees = Decimal("0")
        total_net_liquidation = Decimal("0")
        total_exposure = Decimal("0")

        any_unavailable = False

        for record in records:
            self._validate_record_shape(
                record
            )

            asset_id = _required_text(
                record.asset_id,
                "asset_id",
            ).upper()

            position_id = _required_text(
                record.position_id,
                "position_id",
            )

            if position_id in seen_positions:
                raise PlnPortfolioSnapshotError(
                    "DUPLICATE_POSITION_ID:"
                    + position_id
                )

            seen_positions.add(
                position_id
            )

            try:
                contract = (
                    require_runtime_accounting_contract(
                        asset_id
                    )
                )
            except InstrumentAccountingContractError as exc:
                raise PlnPortfolioSnapshotError(
                    str(exc)
                ) from exc

            native_currency = _required_text(
                record.native_currency,
                "native_currency",
            ).upper()

            if (
                native_currency
                != contract.native_pnl_currency.upper()
            ):
                raise PlnPortfolioSnapshotError(
                    "NATIVE_CURRENCY_MISMATCH:"
                    + asset_id
                )

            record_multiplier = _required_decimal(
                record.pnl_multiplier,
                "pnl_multiplier",
            )

            if (
                record_multiplier
                != contract.pnl_multiplier
            ):
                raise PlnPortfolioSnapshotError(
                    "PNL_MULTIPLIER_MISMATCH:"
                    + asset_id
                )

            freshness = _freshness(
                record.fx_freshness
            )

            age = record.fx_quote_age_seconds

            if age is not None:
                age = _decimal(
                    age,
                    "fx_quote_age_seconds",
                )

                if age < 0:
                    raise PlnPortfolioSnapshotError(
                        "fx_quote_age_seconds cannot be negative"
                    )

                ages.append(
                    age
                )

            if freshness is FxFreshness.FX_STALE:
                if age is None:
                    raise PlnPortfolioSnapshotError(
                        "STALE_FX_REQUIRES_AGE:"
                        + asset_id
                    )

                stale_assets.add(
                    asset_id
                )

            if (
                freshness
                is FxFreshness.FX_UNAVAILABLE
                or not bool(
                    record.pln_available
                )
            ):
                any_unavailable = True
                unavailable_assets.add(
                    asset_id
                )

                for limitation in tuple(
                    record.limitations
                ):
                    limitations.add(
                        str(limitation)
                    )

                continue

            fx_rate = _required_decimal(
                record.fx_rate,
                "fx_rate",
            )

            if fx_rate <= 0:
                raise PlnPortfolioSnapshotError(
                    "fx_rate must be positive"
                )

            unrealized = _required_decimal(
                record.unrealized_pnl_pln,
                "unrealized_pnl_pln",
            )

            exit_fee = _required_decimal(
                record.estimated_exit_fee_pln,
                "estimated_exit_fee_pln",
            )

            net_liquidation = _required_decimal(
                record.estimated_net_liquidation_pnl_pln,
                "estimated_net_liquidation_pnl_pln",
            )

            if exit_fee < 0:
                raise PlnPortfolioSnapshotError(
                    "estimated_exit_fee_pln cannot be negative"
                )

            if (
                unrealized
                - exit_fee
                != net_liquidation
            ):
                raise PlnPortfolioSnapshotError(
                    "MTM_LIQUIDATION_INVARIANT_BROKEN:"
                    + asset_id
                )

            try:
                native_notional = (
                    contract.native_notional(
                        quantity=record.quantity,
                        price=record.mark_price,
                    )
                )
            except InstrumentAccountingContractError as exc:
                raise PlnPortfolioSnapshotError(
                    str(exc)
                ) from exc

            exposure_pln = (
                native_notional
                * fx_rate
            )

            total_unrealized += (
                unrealized
            )

            total_exit_fees += (
                exit_fee
            )

            total_net_liquidation += (
                net_liquidation
            )

            total_exposure += (
                exposure_pln
            )

            for limitation in tuple(
                record.limitations
            ):
                limitations.add(
                    str(limitation)
                )

        max_age = (
            max(ages)
            if ages
            else None
        )

        if any_unavailable:
            limitations.add(
                PORTFOLIO_FX_INCOMPLETE
            )

            return PlnPortfolioSnapshot(
                cash_pln=cash,
                position_count=len(records),
                unrealized_pnl_pln=None,
                estimated_exit_fees_pln=None,
                estimated_net_liquidation_pnl_pln=None,
                equity_pln=None,
                estimated_liquidation_equity_pln=None,
                exposure_pln=None,
                pln_available=False,
                fx_freshness=FxFreshness.FX_UNAVAILABLE,
                max_fx_quote_age_seconds=max_age,
                stale_assets=tuple(
                    sorted(
                        stale_assets
                    )
                ),
                unavailable_assets=tuple(
                    sorted(
                        unavailable_assets
                    )
                ),
                limitations=tuple(
                    sorted(
                        limitations
                    )
                ),
            )

        portfolio_freshness = (
            FxFreshness.FX_STALE
            if stale_assets
            else FxFreshness.FX_FRESH
        )

        equity = (
            cash
            + total_unrealized
        )

        liquidation_equity = (
            cash
            + total_net_liquidation
        )

        return PlnPortfolioSnapshot(
            cash_pln=cash,
            position_count=len(records),
            unrealized_pnl_pln=(
                total_unrealized
            ),
            estimated_exit_fees_pln=(
                total_exit_fees
            ),
            estimated_net_liquidation_pnl_pln=(
                total_net_liquidation
            ),
            equity_pln=equity,
            estimated_liquidation_equity_pln=(
                liquidation_equity
            ),
            exposure_pln=total_exposure,
            pln_available=True,
            fx_freshness=portfolio_freshness,
            max_fx_quote_age_seconds=max_age,
            stale_assets=tuple(
                sorted(
                    stale_assets
                )
            ),
            unavailable_assets=(),
            limitations=tuple(
                sorted(
                    limitations
                )
            ),
        )