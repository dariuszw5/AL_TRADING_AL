from decimal import Decimal

import pytest

from src.execution.capital_admission import (
    ENTRY_FEE_SETTLED_AT_REALIZATION,
    CapitalAdmissionPolicyError,
    CapitalAdmissionReason,
    CashBackedCapitalAdmissionPolicy,
)


def policy():
    return CashBackedCapitalAdmissionPolicy()


def test_allows_exposure_below_full_cash_limit():
    result = policy().evaluate_long_entry(
        settled_cash_pln="1000",
        proposed_exposure_pln="999.99",
        max_exposure_percent="100",
    )

    assert result.allowed is True
    assert (
        result.reason
        is CapitalAdmissionReason.ALLOWED
    )
    assert (
        result.capital_limit_pln
        == Decimal("1000")
    )
    assert (
        result.headroom_pln
        == Decimal("0.01")
    )


def test_allows_exact_limit_without_rounding():
    result = policy().evaluate_long_entry(
        settled_cash_pln="1000",
        proposed_exposure_pln="1000",
        max_exposure_percent="100",
    )

    assert result.allowed is True
    assert (
        result.headroom_pln
        == Decimal("0")
    )


def test_rejects_exposure_above_limit():
    result = policy().evaluate_long_entry(
        settled_cash_pln="1000",
        proposed_exposure_pln="1000.0000000001",
        max_exposure_percent="100",
    )

    assert result.allowed is False
    assert (
        result.reason
        is CapitalAdmissionReason
        .CAPITAL_LIMIT_EXCEEDED
    )
    assert (
        result.headroom_pln
        == Decimal("-0.0000000001")
    )


def test_max_exposure_percent_scales_cash_limit():
    result = policy().evaluate_long_entry(
        settled_cash_pln="1000",
        proposed_exposure_pln="500",
        max_exposure_percent="50",
    )

    assert result.allowed is True
    assert (
        result.capital_limit_pln
        == Decimal("500")
    )


def test_zero_cash_blocks_new_long_entry():
    result = policy().evaluate_long_entry(
        settled_cash_pln="0",
        proposed_exposure_pln="1",
        max_exposure_percent="100",
    )

    assert result.allowed is False
    assert (
        result.reason
        is CapitalAdmissionReason
        .SETTLED_CASH_NONPOSITIVE
    )
    assert (
        result.capital_limit_pln
        == Decimal("0")
    )


def test_negative_cash_blocks_and_clamps_limit_to_zero():
    result = policy().evaluate_long_entry(
        settled_cash_pln="-25.5",
        proposed_exposure_pln="1",
        max_exposure_percent="100",
    )

    assert result.allowed is False
    assert (
        result.reason
        is CapitalAdmissionReason
        .SETTLED_CASH_NONPOSITIVE
    )
    assert (
        result.settled_cash_pln
        == Decimal("-25.5")
    )
    assert (
        result.capital_limit_pln
        == Decimal("0")
    )


def test_missing_authoritative_cash_fails_closed():
    result = policy().evaluate_long_entry(
        settled_cash_pln=None,
        proposed_exposure_pln="10",
        max_exposure_percent="100",
    )

    assert result.allowed is False
    assert (
        result.reason
        is CapitalAdmissionReason
        .CAPITAL_SOURCE_UNAVAILABLE
    )
    assert result.capital_limit_pln is None


def test_missing_exposure_fails_closed():
    result = policy().evaluate_long_entry(
        settled_cash_pln="1000",
        proposed_exposure_pln=None,
        max_exposure_percent="100",
    )

    assert result.allowed is False
    assert (
        result.reason
        is CapitalAdmissionReason
        .EXPOSURE_UNAVAILABLE
    )
    assert (
        result.capital_limit_pln
        == Decimal("1000")
    )


@pytest.mark.parametrize(
    "value",
    [
        "0",
        "-1",
        "NaN",
        "Infinity",
        "-Infinity",
        "not-a-number",
    ],
)
def test_invalid_exposure_fails_closed(
    value,
):
    result = policy().evaluate_long_entry(
        settled_cash_pln="1000",
        proposed_exposure_pln=value,
        max_exposure_percent="100",
    )

    assert result.allowed is False
    assert (
        result.reason
        is CapitalAdmissionReason
        .EXPOSURE_INVALID
    )


@pytest.mark.parametrize(
    "value",
    [
        "0",
        "-1",
        "100.0001",
        "NaN",
        "Infinity",
        None,
    ],
)
def test_invalid_max_exposure_percent_is_configuration_error(
    value,
):
    with pytest.raises(
        CapitalAdmissionPolicyError,
        match="max_exposure_percent",
    ):
        policy().evaluate_long_entry(
            settled_cash_pln="1000",
            proposed_exposure_pln="10",
            max_exposure_percent=value,
        )


def test_decimal_precision_is_preserved():
    result = policy().evaluate_long_entry(
        settled_cash_pln=(
            "999.9891194873119108850427926"
        ),
        proposed_exposure_pln=(
            "999.9891194873119108850427926"
        ),
        max_exposure_percent="100",
    )

    assert result.allowed is True
    assert (
        result.capital_limit_pln
        == Decimal(
            "999.9891194873119108850427926"
        )
    )
    assert (
        result.proposed_exposure_pln
        == Decimal(
            "999.9891194873119108850427926"
        )
    )


def test_entry_fee_limitation_is_explicit_on_every_decision():
    allowed = policy().evaluate_long_entry(
        settled_cash_pln="1000",
        proposed_exposure_pln="1",
        max_exposure_percent="100",
    )

    rejected = policy().evaluate_long_entry(
        settled_cash_pln="1000",
        proposed_exposure_pln="1001",
        max_exposure_percent="100",
    )

    for result in (
        allowed,
        rejected,
    ):
        assert (
            ENTRY_FEE_SETTLED_AT_REALIZATION
            in result.limitations
        )


def test_policy_does_not_accept_legacy_balance_inputs():
    with pytest.raises(
        TypeError,
    ):
        policy().evaluate_long_entry(
            settled_cash_pln="1000",
            proposed_exposure_pln="10",
            max_exposure_percent="100",
            initial_balance="1000000",
        )

    with pytest.raises(
        TypeError,
    ):
        policy().evaluate_long_entry(
            settled_cash_pln="1000",
            proposed_exposure_pln="10",
            max_exposure_percent="100",
            simulation_units="1000000",
        )
