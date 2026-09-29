"""Cost audit checks: pure validation only, no manufactured broker costs."""
from copy import deepcopy

import pytest

from src.research.brain_v36.cost_audit import _metrics, analyze_sealed_validation


def trade(entry=100.0, exit_price=100.1, cost=0.0018, side="LONG"):
    gross = (exit_price / entry - 1) * (1 if side == "LONG" else -1)
    return {
        "entry_mid": entry, "exit_mid": exit_price,
        "return_fraction": gross - cost, "round_trip_cost": cost,
    }


def payload(raw=None, filtered=None):
    raw = [] if raw is None else raw
    filtered = [] if filtered is None else filtered
    def performance(sample):
        return {
            "trades": len(sample),
            "expectancy_net": (
                sum(t["return_fraction"] for t in sample) / len(sample)
                if sample else None
            ),
        }
    record = {
        "symbol": "BTCUSDT", "asset_type": "crypto",
        "fold": 1, "strategy": "trend", "side": "LONG",
        "horizon_minutes": 15, "cost_source": "ASSUMED_NOT_MEASURED",
        "round_trip_cost": 0.0018,
        "unfiltered_validation_trades": raw,
        "validation_trades": filtered,
        "unfiltered_validation": performance(raw),
        "validation": performance(filtered),
        "unfiltered_validation_scan": {"signals": len(raw)},
        "validation_scan": {"signals": len(filtered)},
        "admitted_before_test": False,
        "test_status": "NOT_EVALUATED_VALIDATION_GATE",
        "test": None, "test_scan": None, "test_trades": [],
    }
    return {
        "mode": "RESEARCH_ONLY",
        "runs": [{
            "mode": "RESEARCH_ONLY", "evaluate_test": False,
            "reference_only": False, "instrument_type": "spot",
            "costs": {"round_trip": 0.0018},
            "results": [record],
        }],
    }


def test_gross_net_cost_are_algebraically_reconciled():
    row = analyze_sealed_validation(payload(
        raw=[trade(exit_price=100.1), trade(exit_price=100.5)],
        filtered=[trade(exit_price=100.5)],
    ))[0]
    assert row["raw_mean_gross"] == pytest.approx(0.003)
    assert row["raw_mean_net"] == pytest.approx(0.0012)
    assert row["raw_mean_gross"] - row["raw_mean_net"] == pytest.approx(0.0018)
    assert row["filtered_mean_gross"] == pytest.approx(0.005)
    assert row["raw_cost_effect"] == "POSITIVE_NET_IN_VALIDATION"


def test_cost_can_erase_positive_gross_edge():
    row = analyze_sealed_validation(payload(raw=[trade(exit_price=100.1)]))[0]
    assert row["raw_mean_gross"] == pytest.approx(0.001)
    assert row["raw_mean_net"] == pytest.approx(-0.0008)
    assert row["raw_break_even_cost"] == pytest.approx(0.001)
    assert row["raw_cost_effect"] == "COST_ERASES_GROSS_EDGE"


def test_negative_gross_cannot_be_rescued_by_zero_cost():
    row = analyze_sealed_validation(payload(raw=[trade(exit_price=99.9)]))[0]
    assert row["raw_mean_gross"] < 0
    assert row["raw_cost_effect"] == "NONPOSITIVE_GROSS_EDGE"


def test_empty_raw_and_filtered_samples_are_explicit():
    row = analyze_sealed_validation(payload())[0]
    assert row["raw_trades"] == 0
    assert row["raw_mean_gross"] is None
    assert row["filtered_mean_net"] is None
    assert row["test_status"] == "NOT_EVALUATED_VALIDATION_GATE"


def test_mismatching_exit_return_or_cost_fails_closed():
    altered = payload(raw=[trade()])
    altered["runs"][0]["results"][0]["unfiltered_validation_trades"][0]["return_fraction"] = 100
    with pytest.raises(ValueError, match="reconcile"):
        analyze_sealed_validation(altered)
    wrong_cost = payload(raw=[trade()])
    wrong_cost["runs"][0]["results"][0]["unfiltered_validation_trades"][0]["round_trip_cost"] = 0
    with pytest.raises(ValueError, match="inconsistent cost"):
        analyze_sealed_validation(wrong_cost)


@pytest.mark.parametrize("mutation", ["not_sealed", "test_result", "test_trade", "test_scan"])
def test_test_access_is_refused(mutation):
    report = payload(raw=[trade()])
    row = report["runs"][0]["results"][0]
    if mutation == "not_sealed":
        report["runs"][0]["evaluate_test"] = True
    elif mutation == "test_result":
        row["test"] = {"trades": 1}
    elif mutation == "test_trade":
        row["test_trades"] = [{"return_fraction": 0.42}]
    else:
        row["test_scan"] = {"signals": 1}
    with pytest.raises(ValueError, match="TEST"):
        analyze_sealed_validation(report)


def test_validation_raw_and_filtered_are_independent_series():
    report = payload(raw=[trade(exit_price=100.1), trade(exit_price=100.5)],
                     filtered=[trade(exit_price=100.5)])
    row = analyze_sealed_validation(deepcopy(report))[0]
    assert row["raw_trades"] == 2
    assert row["filtered_trades"] == 1
    assert row["raw_mean_gross"] != row["filtered_mean_gross"]
    assert report["runs"][0]["results"][0]["test"] is None
