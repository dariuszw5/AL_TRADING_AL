from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import Enum


ENTRY_FEE_SETTLED_AT_REALIZATION = (
    "ENTRY_FEE_SETTLED_AT_REALIZATION"
)


class CapitalAdmissionReason(
    str,
    Enum,
):
    ALLOWED = "ALLOWED"
    CAPITAL_SOURCE_UNAVAILABLE = (
        "CAPITAL_SOURCE_UNAVAILABLE"
    )
    SETTLED_CASH_NONPOSITIVE = (
        "SETTLED_CASH_NONPOSITIVE"
    )
    EXPOSURE_UNAVAILABLE = (
        "EXPOSURE_UNAVAILABLE"
    )
    EXPOSURE_INVALID = (
        "EXPOSURE_INVALID"
    )
    CAPITAL_LIMIT_EXCEEDED = (
        "CAPITAL_LIMIT_EXCEEDED"
    )


class CapitalAdmissionPolicyError(
    ValueError
):
    pass


@dataclass(frozen=True)
class CapitalAdmissionDecision:
    allowed: bool
    reason: CapitalAdmissionReason

    settled_cash_pln: Decimal | None
    max_exposure_percent: Decimal
    capital_limit_pln: Decimal | None

    proposed_exposure_pln: Decimal | None
    headroom_pln: Decimal | None

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


def _max_exposure_percent(
    value,
):
    result = _decimal_or_none(
        value
    )

    if (
        result is None
        or result <= 0
        or result > 100
    ):
        raise CapitalAdmissionPolicyError(
            "max_exposure_percent must be "
            "a finite decimal in (0, 100]"
        )

    return result


class CashBackedCapitalAdmissionPolicy:
    """
    Pure Phase 12 cash-backed LONG-entry admission policy.

    Authoritative semantics:

    capital_limit_pln =
        max(0, settled_cash_pln)
        * max_exposure_percent
        / 100

    A proposed LONG entry is admitted only when its already-calculated
    gross exposure PLN is positive, finite and no greater than the
    capital limit.

    This policy does not:
    - read legacy initial_balance,
    - read simulation_units,
    - reserve or debit settled cash,
    - model margin, collateral or leverage,
    - model short financing,
    - calculate FX,
    - calculate slippage,
    - persist capital state,
    - mutate runtime or broker state.

    FX/slippage exposure construction belongs to the later Phase 12
    integration layer. Missing exposure is therefore fail-closed here.

    Entry fee remains governed by:
    ENTRY_FEE_SETTLED_AT_REALIZATION.
    """

    def evaluate_long_entry(
        self,
        *,
        settled_cash_pln,
        proposed_exposure_pln,
        max_exposure_percent,
    ):
        exposure_percent = (
            _max_exposure_percent(
                max_exposure_percent
            )
        )

        cash = _decimal_or_none(
            settled_cash_pln
        )

        limitations = (
            ENTRY_FEE_SETTLED_AT_REALIZATION,
        )

        if cash is None:
            return CapitalAdmissionDecision(
                allowed=False,
                reason=(
                    CapitalAdmissionReason
                    .CAPITAL_SOURCE_UNAVAILABLE
                ),
                settled_cash_pln=None,
                max_exposure_percent=(
                    exposure_percent
                ),
                capital_limit_pln=None,
                proposed_exposure_pln=(
                    _decimal_or_none(
                        proposed_exposure_pln
                    )
                ),
                headroom_pln=None,
                limitations=limitations,
            )

        nonnegative_cash = max(
            cash,
            Decimal("0"),
        )

        capital_limit = (
            nonnegative_cash
            * exposure_percent
            / Decimal("100")
        )

        if cash <= 0:
            return CapitalAdmissionDecision(
                allowed=False,
                reason=(
                    CapitalAdmissionReason
                    .SETTLED_CASH_NONPOSITIVE
                ),
                settled_cash_pln=cash,
                max_exposure_percent=(
                    exposure_percent
                ),
                capital_limit_pln=(
                    capital_limit
                ),
                proposed_exposure_pln=(
                    _decimal_or_none(
                        proposed_exposure_pln
                    )
                ),
                headroom_pln=None,
                limitations=limitations,
            )

        if proposed_exposure_pln is None:
            return CapitalAdmissionDecision(
                allowed=False,
                reason=(
                    CapitalAdmissionReason
                    .EXPOSURE_UNAVAILABLE
                ),
                settled_cash_pln=cash,
                max_exposure_percent=(
                    exposure_percent
                ),
                capital_limit_pln=(
                    capital_limit
                ),
                proposed_exposure_pln=None,
                headroom_pln=None,
                limitations=limitations,
            )

        proposed_exposure = (
            _decimal_or_none(
                proposed_exposure_pln
            )
        )

        if (
            proposed_exposure is None
            or proposed_exposure <= 0
        ):
            return CapitalAdmissionDecision(
                allowed=False,
                reason=(
                    CapitalAdmissionReason
                    .EXPOSURE_INVALID
                ),
                settled_cash_pln=cash,
                max_exposure_percent=(
                    exposure_percent
                ),
                capital_limit_pln=(
                    capital_limit
                ),
                proposed_exposure_pln=(
                    proposed_exposure
                ),
                headroom_pln=None,
                limitations=limitations,
            )

        headroom = (
            capital_limit
            - proposed_exposure
        )

        if proposed_exposure > capital_limit:
            return CapitalAdmissionDecision(
                allowed=False,
                reason=(
                    CapitalAdmissionReason
                    .CAPITAL_LIMIT_EXCEEDED
                ),
                settled_cash_pln=cash,
                max_exposure_percent=(
                    exposure_percent
                ),
                capital_limit_pln=(
                    capital_limit
                ),
                proposed_exposure_pln=(
                    proposed_exposure
                ),
                headroom_pln=headroom,
                limitations=limitations,
            )

        return CapitalAdmissionDecision(
            allowed=True,
            reason=(
                CapitalAdmissionReason
                .ALLOWED
            ),
            settled_cash_pln=cash,
            max_exposure_percent=(
                exposure_percent
            ),
            capital_limit_pln=(
                capital_limit
            ),
            proposed_exposure_pln=(
                proposed_exposure
            ),
            headroom_pln=headroom,
            limitations=limitations,
        )
