"""Interval-generalization: wall-clock horizon, session gaps and sealed TEST."""
from math import sin

import pytest

from src.data.candle import Candle
from src.research.brain_v36 import CostProfile, RiskPlan, walk_forward, validate_history
from src.research.brain_v36.engine import contiguous, features, folds, label_outcome


COSTS = CostProfile(
    commission_per_side=0.0004,
    spread_round_trip=0.0002,
    slippage_per_side=0.0005,
    source="EXPLICIT_SYNTHETIC_TEST_ASSUMPTION",
)


def flat_bar(index, *, bar_minutes=5, price=100.0, timestamp=None):
    return Candle(
        timestamp=index * bar_minutes * 60_000 if timestamp is None else timestamp,
        open=price, high=price + 0.01, low=price - 0.01,
        close=price, volume=1.0,
    )


def wave(n=1100, *, bar_minutes=5):
    candles = []
    prev = 100.0
    for i in range(n):
        close = 100 + 0.003 * i + sin(i / 9) * 1.4
        candles.append(Candle(
            timestamp=i * bar_minutes * 60_000,
            open=prev,
            high=max(close, prev) + 0.1,
            low=min(close, prev) - 0.1,
            close=close, volume=5.0,
        ))
        prev = close
    return candles


def test_1m_remains_default_and_5m_has_exact_horizon_in_bars():
    one = RiskPlan(horizon_minutes=15)
    five = RiskPlan(horizon_minutes=15, bar_minutes=5)
    assert one.bar_minutes == 1
    assert one.horizon_bars == 15
    assert one.candle_duration_ms == 60_000
    assert five.horizon_bars == 3
    assert five.candle_duration_ms == 300_000
    assert RiskPlan(horizon_minutes=60, bar_minutes=5).horizon_bars == 12


@pytest.mark.parametrize("horizon,bar", [(15, 0), (15, 2), (15, 7), (15, 90), (15, True), (15, 1.5)])
def test_rejects_invalid_or_nondivisible_timeframe(horizon, bar):
    with pytest.raises(ValueError):
        RiskPlan(horizon_minutes=horizon, bar_minutes=bar)


def test_5minute_horizon_executes_next_open_and_times_out_after_15_real_minutes():
    candles = [flat_bar(i) for i in range(5)]
    result = label_outcome(
        candles, 0, "LONG",
        RiskPlan(horizon_minutes=15, bar_minutes=5),
        COSTS,
    )
    assert result["entry_index"] == 1
    assert result["exit_index"] == 3
    assert result["signal_timestamp"] == 0
    assert result["entry_timestamp"] == 300_000
    assert result["exit_timestamp"] == 900_000
    assert result["reason"] == "TIME_EXIT"
    assert result["return_fraction"] == pytest.approx(-COSTS.round_trip)


def test_5minute_stop_first_when_ohlc_touches_both_barriers():
    candles = [flat_bar(0), Candle(
        timestamp=300_000, open=105, high=120, low=85,
        close=106, volume=1,
    )]
    risk = RiskPlan(horizon_minutes=5, bar_minutes=5)
    result = label_outcome(candles, 0, "LONG", risk, COSTS)
    assert result["entry_mid"] == 105
    assert result["reason"] == "STOP_LOSS"
    assert result["exit_mid"] == pytest.approx(105 * (1 - risk.stop_fraction))


def test_gap_after_close_censors_open_position_and_is_never_filled():
    candles = [flat_bar(0), flat_bar(1), flat_bar(2),
               flat_bar(3, timestamp=24 * 60 * 60_000)]
    risk = RiskPlan(horizon_minutes=15, bar_minutes=5)
    assert not contiguous(candles, 0, 3, bar_minutes=5)
    assert label_outcome(candles, 0, "LONG", risk, COSTS) is None


def test_contiguous_5minute_features_only_use_past_complete_bars():
    candles = wave(75)
    before = features(candles, 35, bar_minutes=5)
    candles[60].high += 50
    candles[60].close += 50
    assert features(candles, 35, bar_minutes=5) == before
    candles[37].timestamp += 60_000
    with pytest.raises(ValueError, match="consecutive"):
        features(candles, 45, bar_minutes=5)


def test_as_of_uses_entire_5min_candle_duration():
    candles = [flat_bar(i) for i in range(4)]
    finish = candles[-1].timestamp + 300_000
    assert validate_history(candles, as_of_ms=finish, bar_minutes=5)
    with pytest.raises(ValueError, match="forming"):
        validate_history(candles, as_of_ms=finish - 1, bar_minutes=5)


def test_5min_fold_embargo_is_15_wall_clock_minutes_not_75():
    risk = RiskPlan(horizon_minutes=15, bar_minutes=5)
    result = folds(1100, risk, initial_train=450,
                   validation_size=250, test_size=250)
    assert result[0].embargo == 3
    candles = wave()
    f = result[0]
    assert candles[f.validation_start].timestamp - candles[f.train_end].timestamp == 15 * 60_000
    assert candles[f.test_start].timestamp - candles[f.validation_end].timestamp == 15 * 60_000


def test_walk_forward_5minute_is_pure_and_keeps_test_sealed(tmp_path):
    candles = wave()
    risk = RiskPlan(horizon_minutes=15, bar_minutes=5, min_train_samples=2)
    result = walk_forward(
        candles, symbol="BTCUSDT", asset_type="crypto",
        instrument_type="spot", costs=COSTS, risk=risk,
        initial_train=450, validation_size=250, test_size=250,
        evaluate_test=False,
    )
    assert result["mode"] == "RESEARCH_ONLY"
    assert result["bar_minutes"] == 5
    assert result["risk"]["horizon_minutes"] == 15
    assert result["risk"]["bar_minutes"] == 5
    assert all(row["bar_minutes"] == 5 and row["feature_window_bars"] == 20
               for row in result["results"])
    assert all(row["test"] is None and row["test_scan"] is None
               for row in result["results"])
    assert not list(tmp_path.iterdir())


def test_declaring_1m_data_as_5m_does_not_silently_return_zero_signals():
    candles = wave(bar_minutes=1)
    with pytest.raises(ValueError, match="declared candle interval"):
        walk_forward(
            candles, symbol="BTCUSDT", asset_type="crypto",
            instrument_type="spot", costs=COSTS,
            risk=RiskPlan(horizon_minutes=15, bar_minutes=5),
            initial_train=450, validation_size=250, test_size=250,
            evaluate_test=False,
        )


def test_existing_default_1m_output_is_same_as_explicit_1m():
    candles = wave(bar_minutes=1)
    kwargs = dict(
        symbol="BTCUSDT", asset_type="crypto", instrument_type="spot",
        costs=COSTS, initial_train=450, validation_size=250,
        test_size=250, evaluate_test=False,
    )
    implicit = walk_forward(candles, risk=RiskPlan(horizon_minutes=15), **kwargs)
    explicit = walk_forward(candles, risk=RiskPlan(horizon_minutes=15, bar_minutes=1), **kwargs)
    assert implicit == explicit
