"""Offline tests: chronological isolation, cost provenance, no live mutations."""
import copy
from math import sin

import pytest

from src.data.candle import Candle
from src.research.brain_v36 import CostProfile, RiskPlan, cost_for_symbol, validate_history, walk_forward
from src.research.brain_v36.engine import (
    contiguous, features, folds, label_outcome, performance, signal_side,
    _training, _observe_period,
)


def profile(cost=0.0004):
    return CostProfile(cost, 0.0002, 0.0005, "SYNTHETIC_UNIT_TEST_ASSUMPTION")


def bar(index, *, opening=100.0, close=100.0, high=None, low=None, timestamp=None):
    return Candle(
        timestamp=index * 60_000 if timestamp is None else timestamp,
        open=opening,
        high=max(opening, close) + 0.1 if high is None else high,
        low=min(opening, close) - 0.1 if low is None else low,
        close=close,
        volume=10.0,
    )


def wave(size=1100):
    result = []
    previous = 100.0
    for i in range(size):
        close = 100.0 + 0.003 * i + sin(i / 9) * 1.4
        result.append(bar(i, opening=previous, close=close))
        previous = close
    return result


def test_costs_are_explicit_and_subtract_full_round_trip():
    cost = profile()
    assert cost.round_trip == pytest.approx(0.002)
    assert cost.net_fraction(100, 101, "LONG") == pytest.approx(0.008)
    assert cost.net_fraction(100, 99, "SHORT") == pytest.approx(0.008)
    with pytest.raises(ValueError):
        CostProfile(0, 0, 0, "")
    with pytest.raises(ValueError):
        CostProfile(0.0004, float("nan"), 0, "bad")
    with pytest.raises(KeyError):
        CostProfile.from_mapping({"commission_per_side": 0, "source": "incomplete"})


def test_cost_resolution_is_per_symbol_or_asset_class_and_never_invents_missing_costs():
    config = {
        "crypto": dict(commission_per_side=0.001, spread_round_trip=0.001,
                       slippage_per_side=0.001, source="EXAMPLE"),
        "ETHUSDT": dict(commission_per_side=0.002, spread_round_trip=0.001,
                        slippage_per_side=0.001, source="SYMBOL_OVERRIDE"),
    }
    cost, meta = cost_for_symbol("ETHUSDT", config)
    assert cost.source == "SYMBOL_OVERRIDE"
    assert meta["asset_type"] == "crypto"
    dynamic, meta = cost_for_symbol("ETHFIUSDT", config)
    assert dynamic.source == "EXAMPLE"
    with pytest.raises(ValueError, match="No cost model"):
        cost_for_symbol("EURUSD", config)



def test_legacy_get_asset_resolver_is_compatible_without_keyword(monkeypatch):
    from src.data import assets
    from src.research.brain_v36 import costs

    original = assets.get_asset

    def old_get_asset(symbol):
        if symbol == "ETHUSDT":
            return original(symbol)
        raise ValueError("Symbol absent in the old registry")

    monkeypatch.setattr(costs.asset_registry, "get_asset", old_get_asset)
    settings = {
        "crypto": dict(commission_per_side=0.001, spread_round_trip=0.001,
                       slippage_per_side=0.001, source="EXPLICIT_CRYPTO_ASSUMPTION"),
        "index": dict(commission_per_side=0.001, spread_round_trip=0.001,
                      slippage_per_side=0.001, source="EXPLICIT_INDEX_PROXY_ASSUMPTION"),
    }
    assert cost_for_symbol("ETHUSDT", settings)[1]["asset_type"] == "crypto"
    assert cost_for_symbol("ETHFIUSDT", settings)[1]["asset_type"] == "crypto"
    assert cost_for_symbol("SP500_INDEX", settings)[1]["reference_only"] is True
    with pytest.raises(ValueError, match="Unknown research asset"):
        cost_for_symbol("UNSUPPORTED_UNKNOWN", settings)


def test_nonexecuting_reference_indices_are_flagged():
    raw = dict(commission_per_side=0.001, spread_round_trip=0.002,
               slippage_per_side=0.001, source="SYNTHETIC")
    _, meta = cost_for_symbol("SP500_INDEX", {"index": raw})
    assert meta["reference_only"] is True


def test_candle_validation_rejects_bad_history_and_unclosed_last():
    good = [bar(0), bar(1), bar(2)]
    assert validate_history(good, as_of_ms=180_000)
    with pytest.raises(ValueError, match="forming"):
        validate_history(good, as_of_ms=170_000)
    with pytest.raises(ValueError, match="Duplicate"):
        validate_history([bar(0), bar(1), bar(1)])
    with pytest.raises(ValueError, match="OHLC"):
        validate_history([bar(0, high=99.0)])
    with pytest.raises(ValueError, match="Nonfinite"):
        validate_history([bar(0, close=float("nan"))])


def test_features_read_only_past_data_and_strategy_direction():
    candles = wave(80)
    earlier = features(candles, 35)
    candles[70].open *= 1.5
    candles[70].high *= 1.5
    candles[70].close *= 1.5
    assert features(candles, 35) == earlier
    assert signal_side("trend", candles, 35) in {"LONG", "SHORT", None}


def test_execution_enters_only_at_next_open_and_is_stop_first():
    candle0 = bar(0, opening=100, close=100)
    candle1 = bar(1, opening=105, close=106, high=120, low=85)
    risk = RiskPlan(horizon_minutes=1)
    trade = label_outcome([candle0, candle1], 0, "LONG", risk, profile())
    assert trade["entry_mid"] == 105
    assert trade["exit_mid"] == pytest.approx(105 * (1 - risk.stop_fraction))
    assert trade["reason"] == "STOP_LOSS"
    assert trade["return_fraction"] == pytest.approx(-risk.stop_fraction - profile().round_trip)


def test_gap_after_early_stop_does_not_retroactively_censor_trade():
    candles = [
        bar(0), bar(1, opening=100, close=90, low=89),
        bar(3, opening=90, close=90),
    ]
    result = label_outcome(candles, 0, "LONG", RiskPlan(horizon_minutes=2), profile())
    assert result["exit_index"] == 1
    assert result["reason"] == "STOP_LOSS"


def test_future_gap_while_position_open_is_censored_not_filled():
    candles = [bar(0), bar(1), bar(3)]
    assert label_outcome(candles, 0, "LONG", RiskPlan(horizon_minutes=2), profile()) is None
    assert not contiguous(candles, 0, 2)


def test_chronological_folds_respect_embargo_and_do_not_overlap_test():
    risk = RiskPlan(horizon_minutes=15)
    result = folds(2500, risk, initial_train=800, validation_size=300, test_size=300)
    assert result
    first = result[0]
    assert first.validation_start >= first.train_end + risk.horizon_minutes
    assert first.test_start >= first.validation_end + risk.horizon_minutes
    assert result[1].test_start >= first.test_end
    with pytest.raises(ValueError, match="Embargo"):
        folds(2500, risk, initial_train=800, validation_size=300, test_size=300, embargo=2)


def test_training_labels_never_cross_train_boundary():
    candles = wave()
    risk = RiskPlan(horizon_minutes=15, min_train_samples=2)
    fold = folds(len(candles), risk, initial_train=450,
                 validation_size=250, test_size=250)[0]
    for strategy in ("trend", "mean_reversion", "breakout"):
        for side in ("LONG", "SHORT"):
            examples = _training(candles, fold, strategy, side, risk, profile())
            assert all(exit_index < fold.train_end for _, _, exit_index in examples)


def test_research_only_report_and_test_not_used_for_validation_decision(tmp_path):
    candles = wave(1100)
    risk = RiskPlan(horizon_minutes=15, min_train_samples=2, min_validation_trades=1)
    args = dict(symbol="BTCUSDT", asset_type="crypto", instrument_type="spot",
                costs=profile(), risk=risk, initial_train=450,
                validation_size=250, test_size=250)
    report = walk_forward(candles, **args)
    assert report["mode"] == "RESEARCH_ONLY"
    assert len(report["results"]) == 6
    assert not list(tmp_path.iterdir())  # engine writes no live or research files
    fold = report["folds"][0]
    assert all(
        r["max_train_label_exit_index"] is None
        or r["max_train_label_exit_index"] < fold["train_end"]
        for r in report["results"]
    )
    altered = copy.deepcopy(candles)
    for i in range(fold["test_start"], fold["test_end"]):
        # Change TEST prices without affecting earlier windows/training/admission.
        altered[i].open *= 1.01
        altered[i].high *= 1.01
        altered[i].low *= 1.01
        altered[i].close *= 1.01
    again = walk_forward(altered, **args)
    for before, after in zip(report["results"], again["results"]):
        assert before["training_samples"] == after["training_samples"]
        assert before["validation"] == after["validation"]
        assert before["admitted_before_test"] == after["admitted_before_test"]



def test_validation_funnel_explains_sparse_signals_and_reconciles():
    candles = wave(450)
    risk = RiskPlan(horizon_minutes=15, min_train_samples=2)
    trades, scan = _observe_period(
        candles, 100, 350,
        strategy="trend", side="LONG",
        training=[], risk=risk, costs=profile(),
    )
    assert trades == []
    assert scan["signals"] > 0
    assert scan["missing_training"] == scan["signals"]
    assert scan["executed_proxy"] == 0

    training = [
        (features(candles, 80), -0.002, 81),
        (features(candles, 81), -0.003, 82),
    ]
    trades, scan = _observe_period(
        candles, 100, 350,
        strategy="trend", side="LONG",
        training=training, risk=risk, costs=profile(),
    )
    assert not trades
    assert scan["signals"] > 0
    assert scan["rejected_nonpositive"] == scan["signals"]
    assert sum(scan[field] for field in (
        "missing_training", "rejected_nonpositive",
        "rejected_uncertainty", "unpriceable_gaps", "executed_proxy",
    )) == scan["signals"]


def test_performance_keeps_empty_research_separate_from_profit():
    empty = performance([])
    assert empty["expectancy_net"] is None
    assert empty["profit_factor"] is None
    wins = performance([{"return_fraction": 0.01}])
    assert wins["trades"] == 1
    assert wins["profit_factor"] is None
