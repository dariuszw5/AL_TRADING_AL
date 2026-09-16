import pytest

from scripts.run_realistic_v2_execution_benchmark import (
    run_benchmark,
)


def test_realistic_v2_execution_benchmark():
    result = run_benchmark()

    assert (
        result["label"]
        == (
            "DETERMINISTIC_EXECUTION_FIXTURE_"
            "NOT_MARKET_PERFORMANCE"
        )
    )

    assert (
        result["entry_reference_price"]
        == pytest.approx(
            10001.0
        )
    )

    assert (
        result["entry_execution_price"]
        == pytest.approx(
            10002.0001
        )
    )

    assert (
        result["entry_spread"]
        == pytest.approx(
            2.0
        )
    )

    assert (
        result["entry_slippage"]
        == pytest.approx(
            1.0001
        )
    )

    assert (
        result["entry_fee"]
        == pytest.approx(
            0.0400080004
        )
    )

    assert (
        result["exit_reference_price"]
        == pytest.approx(
            10049.0
        )
    )

    assert (
        result["exit_execution_price"]
        == pytest.approx(
            10047.9951
        )
    )

    assert (
        result["exit_spread"]
        == pytest.approx(
            2.0
        )
    )

    assert (
        result["exit_slippage"]
        == pytest.approx(
            1.0049
        )
    )

    assert (
        result["exit_fee"]
        == pytest.approx(
            0.0401919804
        )
    )

    assert (
        result["config_hash_match"]
        is True
    )

    assert (
        result[
            "positions_after_round_trip"
        ]
        == ()
    )
