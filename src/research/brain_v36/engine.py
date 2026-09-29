"""Independent, offline walk-forward evaluator for Brain v3.6.

Frozen TRAIN fits a strategy- AND side-conditioned k-NN on previously completed
trades. VALIDATION alone decides admission. TEST is never used for admission,
feature scaling, threshold selection or model fitting. Signal at close(i),
fill at open(i+1); conservative stop-first execution on ambiguous OHLC bars.

This module has NO AIPaperManager, live storage, API, order or funding imports.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isfinite, sqrt
from statistics import mean, pstdev
from typing import Sequence

from .costs import CostProfile

MINUTE_MS = 60_000
STRATEGIES = ("trend", "mean_reversion", "breakout")
SIDES = ("LONG", "SHORT")


@dataclass(frozen=True)
class RiskPlan:
    horizon_minutes: int = 15
    stop_fraction: float = 0.012
    take_fraction: float = 0.024
    neighbors: int = 12
    min_train_samples: int = 8
    min_validation_trades: int = 4
    min_conservative_edge: float = 0.0

    def __post_init__(self) -> None:
        if not 1 <= self.horizon_minutes <= 240:
            raise ValueError("Invalid horizon")
        if not 0 < self.stop_fraction < 1 or not 0 < self.take_fraction < 1:
            raise ValueError("Stop/take must be positive fractions below 1")
        if self.neighbors < 1 or self.min_train_samples < 2 or self.min_validation_trades < 1:
            raise ValueError("Invalid minimum evidence requirement")
        if not isfinite(self.min_conservative_edge) or self.min_conservative_edge < 0:
            raise ValueError("Conservative edge threshold must be non-negative")


@dataclass(frozen=True)
class Fold:
    train_end: int
    validation_start: int
    validation_end: int
    test_start: int
    test_end: int
    embargo: int

    def as_dict(self) -> dict:
        return asdict(self)


def validate_history(candles: Sequence, *, as_of_ms: int | None = None) -> tuple:
    """Inspect real/frozen input without altering or filling missing sessions."""
    if not candles:
        raise ValueError("No candles supplied")
    previous = None
    for bar in candles:
        ts = bar.timestamp
        if isinstance(ts, bool) or not isinstance(ts, int) or ts < 0:
            raise ValueError("Invalid millisecond timestamp")
        values = (bar.open, bar.high, bar.low, bar.close, bar.volume)
        if any(not isfinite(float(v)) for v in values):
            raise ValueError("Nonfinite market data")
        if bar.low <= 0 or bar.volume < 0:
            raise ValueError("Nonpositive price or negative volume")
        if not bar.low <= min(bar.open, bar.close) <= max(bar.open, bar.close) <= bar.high:
            raise ValueError("Malformed OHLC")
        if previous is not None and ts <= previous:
            raise ValueError("Duplicate or unsorted candle")
        previous = ts
    if as_of_ms is not None and candles[-1].timestamp + MINUTE_MS > as_of_ms:
        raise ValueError("Latest candle is still forming")
    return tuple(candles)


def contiguous(candles: Sequence, first: int, last: int) -> bool:
    """Both endpoints inclusive. Preserve actual exchange/session gaps."""
    if first < 0 or last >= len(candles) or first > last:
        return False
    return all(
        candles[j].timestamp - candles[j - 1].timestamp == MINUTE_MS
        for j in range(first + 1, last + 1)
    )


def folds(
    length: int, risk: RiskPlan, *,
    initial_train: int = 1200,
    validation_size: int = 400,
    test_size: int = 400,
    step: int | None = None,
    embargo: int | None = None,
) -> list[Fold]:
    """Expanding chronological folds; test blocks do not overlap by default."""
    margin = risk.horizon_minutes if embargo is None else embargo
    stride = test_size if step is None else step
    if margin < risk.horizon_minutes:
        raise ValueError("Embargo must be >= the full trade horizon")
    if initial_train < risk.horizon_minutes + 30:
        raise ValueError("Initial training window is too short")
    if min(validation_size, test_size) <= risk.horizon_minutes + 1 or stride < test_size:
        raise ValueError("Validation/test/step windows cannot overlap or be empty")
    result = []
    end_train = initial_train
    while True:
        start_val = end_train + margin
        end_val = start_val + validation_size
        start_test = end_val + margin
        end_test = start_test + test_size
        if end_test > length:
            break
        result.append(Fold(end_train, start_val, end_val, start_test, end_test, margin))
        end_train += stride
    if not result:
        raise ValueError("Dataset too short for a sealed TRAIN/VALIDATION/TEST fold")
    return result


def features(candles: Sequence, i: int) -> tuple[float, ...]:
    """Same four normalized past-only features as the v3.5 reference model."""
    if i < 20 or not contiguous(candles, i - 20, i):
        raise ValueError("Insufficient consecutive PAST bars for features")
    closes = [bar.close for bar in candles[i - 20 : i + 1]]
    returns = [b / a - 1 for a, b in zip(closes, closes[1:])]
    volatility = max(pstdev(returns), 0.0001)
    return (
        returns[-1] / volatility,
        (closes[-1] / closes[-6] - 1) / (volatility * sqrt(5)),
        (closes[-1] / closes[0] - 1) / (volatility * sqrt(20)),
        (closes[-1] / mean(closes) - 1) / (volatility * sqrt(20)),
    )


def signal_side(strategy: str, candles: Sequence, i: int) -> str | None:
    """Frozen v3.5 candidate definitions; a new conditional model judges them."""
    f = features(candles, i)
    if strategy == "trend":
        if f[1] > 0.35 and f[2] > 0.35:
            return "LONG"
        if f[1] < -0.35 and f[2] < -0.35:
            return "SHORT"
        return None
    if strategy == "mean_reversion":
        if f[3] < -0.50 and f[0] > 0:
            return "LONG"
        if f[3] > 0.50 and f[0] < 0:
            return "SHORT"
        return None
    if strategy == "breakout":
        previous_high = max(bar.high for bar in candles[i - 20 : i])
        previous_low = min(bar.low for bar in candles[i - 20 : i])
        if candles[i].close > previous_high:
            return "LONG"
        if candles[i].close < previous_low:
            return "SHORT"
        return None
    raise ValueError(f"Unknown strategy {strategy!r}")


def label_outcome(
    candles: Sequence, signal_index: int, side: str, risk: RiskPlan,
    costs: CostProfile,
) -> dict | None:
    """Return None for unpriceable session/data gap; never invent an exit."""
    if side not in SIDES or signal_index < 0 or signal_index + risk.horizon_minutes >= len(candles):
        raise ValueError("Invalid signal/side/horizon")
    entry = float(candles[signal_index + 1].open)
    previous_ts = candles[signal_index].timestamp
    stop = entry * (1 - risk.stop_fraction if side == "LONG" else 1 + risk.stop_fraction)
    take = entry * (1 + risk.take_fraction if side == "LONG" else 1 - risk.take_fraction)

    for j in range(signal_index + 1, signal_index + risk.horizon_minutes + 1):
        bar = candles[j]
        if bar.timestamp - previous_ts != MINUTE_MS:
            return None
        previous_ts = bar.timestamp

        # Gap at next session OPEN is treated before within-bar stop/take.
        if side == "LONG":
            if bar.open <= stop:
                price, reason = bar.open, "STOP_GAP"
            elif bar.open >= take:
                price, reason = take, "TAKE_PROFIT"
            elif bar.low <= stop:
                price, reason = stop, "STOP_LOSS"
            elif bar.high >= take:
                price, reason = take, "TAKE_PROFIT"
            else:
                price, reason = None, None
        else:
            if bar.open >= stop:
                price, reason = bar.open, "STOP_GAP"
            elif bar.open <= take:
                price, reason = take, "TAKE_PROFIT"
            elif bar.high >= stop:
                price, reason = stop, "STOP_LOSS"
            elif bar.low <= take:
                price, reason = take, "TAKE_PROFIT"
            else:
                price, reason = None, None
        if price is None and j == signal_index + risk.horizon_minutes:
            price, reason = bar.close, "TIME_EXIT"
        if price is not None:
            return {
                "signal_index": signal_index,
                "entry_index": signal_index + 1,
                "exit_index": j,
                "signal_timestamp": candles[signal_index].timestamp,
                "entry_timestamp": candles[signal_index + 1].timestamp,
                "exit_timestamp": bar.timestamp,
                "entry_mid": entry,
                "exit_mid": float(price),
                "reason": reason,
                "return_fraction": costs.net_fraction(entry, float(price), side),
                "round_trip_cost": costs.round_trip,
            }
    raise AssertionError("Missing deterministic time exit")


def _training(
    candles: Sequence, fold: Fold, strategy: str, side: str,
    risk: RiskPlan, costs: CostProfile,
) -> list[tuple[tuple[float, ...], float, int]]:
    samples = []
    last_exit = -1
    # train labels must CLOSE before train_end, with no future labels crossing.
    for i in range(20, fold.train_end - risk.horizon_minutes):
        if i <= last_exit or not contiguous(candles, i - 20, i):
            continue
        x = features(candles, i)
        if signal_side(strategy, candles, i) != side:
            continue
        labeled = label_outcome(candles, i, side, risk, costs)
        if labeled is None:
            continue
        if labeled["exit_index"] >= fold.train_end:
            raise AssertionError("Training label crossed TRAIN boundary")
        samples.append((x, labeled["return_fraction"], labeled["exit_index"]))
        last_exit = labeled["exit_index"]
    return samples


def _predict(
    x: tuple[float, ...], training: list, risk: RiskPlan,
) -> tuple[float, float] | None:
    if len(training) < risk.min_train_samples:
        return None
    closest = sorted(
        training,
        key=lambda row: sum((a - b) ** 2 for a, b in zip(x, row[0])),
    )[:risk.neighbors]
    values = [row[1] for row in closest]
    return mean(values), pstdev(values) if len(values) > 1 else 0.0


def _observe_period(
    candles: Sequence, start: int, end: int, *,
    strategy: str, side: str, training: list, risk: RiskPlan, costs: CostProfile,
) -> tuple[list[dict], dict]:
    trades = []
    examined = 0
    signal_count = 0
    missing_training = 0
    rejected_nonpositive = 0
    rejected_uncertainty = 0
    unpriceable = 0
    last_exit = start - 1
    # All labels must EXIT within the specified VALIDATION or TEST block.
    for i in range(max(start, 20), end - risk.horizon_minutes):
        if i <= last_exit or not contiguous(candles, i - 20, i):
            continue
        examined += 1
        x = features(candles, i)
        if signal_side(strategy, candles, i) != side:
            continue
        signal_count += 1
        prediction = _predict(x, training, risk)
        if prediction is None:
            missing_training += 1
            continue
        expectation, uncertainty = prediction
        conservative = expectation - 0.35 * uncertainty
        # Threshold is fixed BEFORE consulting validation/test outcomes.
        if expectation <= 0:
            rejected_nonpositive += 1
            continue
        if conservative <= risk.min_conservative_edge:
            rejected_uncertainty += 1
            continue
        labeled = label_outcome(candles, i, side, risk, costs)
        if labeled is None:
            unpriceable += 1
            continue
        if labeled["exit_index"] >= end:
            raise AssertionError("Outcome escaped its chronological split")
        trades.append({
            **labeled,
            "strategy": strategy,
            "side": side,
            "expected_net_return": expectation,
            "neighbor_spread": uncertainty,
            "conservative_score": conservative,
        })
        last_exit = labeled["exit_index"]
    scan = {
        "examined": examined,
        "signals": signal_count,
        "missing_training": missing_training,
        "rejected_nonpositive": rejected_nonpositive,
        "rejected_uncertainty": rejected_uncertainty,
        "unpriceable_gaps": unpriceable,
        "executed_proxy": len(trades),
    }
    if signal_count != sum(
        scan[name] for name in (
            "missing_training", "rejected_nonpositive",
            "rejected_uncertainty", "unpriceable_gaps", "executed_proxy"
        )
    ):
        raise AssertionError("Validation funnel does not reconcile")
    return trades, scan


def observe_unfiltered_period(
    candles: Sequence, start: int, end: int, *,
    strategy: str, side: str, risk: RiskPlan, costs: CostProfile,
) -> tuple[list[dict], dict]:
    """Counterfactual VALIDATION observation with NO k-NN filter.

    This is a diagnostic of the original strategy's signals under the SAME
    entry/exit/cost assumptions. It is never an entry decision, a live trade,
    a permission to bypass the model, or a reason to admit a TEST candidate.
    Its independent non-overlap path differs from the filtered path.
    """
    trades: list[dict] = []
    signals = occupied = gaps = 0
    last_exit = start - 1
    for i in range(max(start, 20), end - risk.horizon_minutes):
        if not contiguous(candles, i - 20, i):
            continue
        if signal_side(strategy, candles, i) != side:
            continue
        signals += 1
        if i <= last_exit:
            occupied += 1
            continue
        labeled = label_outcome(candles, i, side, risk, costs)
        if labeled is None:
            gaps += 1
            continue
        if labeled["exit_index"] >= end:
            raise AssertionError("Unfiltered observation escaped VALIDATION")
        trades.append({
            **labeled,
            "strategy": strategy,
            "side": side,
            "counterfactual": True,
            "model_filter_applied": False,
        })
        last_exit = labeled["exit_index"]
    scan = {
        "signals": signals,
        "skipped_during_position": occupied,
        "unpriceable_gaps": gaps,
        "completed_proxy": len(trades),
    }
    if signals != occupied + gaps + len(trades):
        raise AssertionError("Unfiltered validation funnel does not reconcile")
    return trades, scan

def performance(trades: Sequence[dict]) -> dict:
    returns = [float(trade["return_fraction"]) for trade in trades]
    if not returns:
        return {
            "trades": 0, "win_rate": None, "expectancy_net": None,
            "profit_factor": None, "max_drawdown_fraction": None,
            "compounded_return_fraction": None,
        }
    gains = sum(max(v, 0) for v in returns)
    losses = -sum(min(v, 0) for v in returns)
    equity = peak = 1.0
    max_drawdown = 0.0
    for ret in returns:
        equity *= max(0.0, 1 + ret)
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, (peak - equity) / peak)
    return {
        "trades": len(returns),
        "win_rate": sum(v > 0 for v in returns) / len(returns),
        "expectancy_net": mean(returns),
        "profit_factor": gains / losses if losses > 0 else None,
        "max_drawdown_fraction": max_drawdown,
        "compounded_return_fraction": equity - 1.0,
    }


def walk_forward(
    candles: Sequence,
    *,
    symbol: str,
    asset_type: str,
    instrument_type: str,
    costs: CostProfile,
    risk: RiskPlan,
    initial_train: int = 1200,
    validation_size: int = 400,
    test_size: int = 400,
    step: int | None = None,
    as_of_ms: int | None = None,
) -> dict:
    """Return an independent RESEARCH_ONLY report; no external side effects."""
    bars = validate_history(candles, as_of_ms=as_of_ms)
    if not isinstance(symbol, str) or not symbol:
        raise ValueError("A real instrument symbol is required")
    if not isinstance(costs, CostProfile):
        raise ValueError("An explicit cost profile is mandatory")
    sections = folds(
        len(bars), risk, initial_train=initial_train,
        validation_size=validation_size, test_size=test_size, step=step,
    )
    proxy = instrument_type in {
        "index_reference", "fx_spot_reference", "continuous_future_proxy"
    }
    rows = []
    for n, fold in enumerate(sections, 1):
        for strategy in STRATEGIES:
            for side in SIDES:
                training = _training(bars, fold, strategy, side, risk, costs)
                validation, val_scan = _observe_period(
                    bars, fold.validation_start, fold.validation_end,
                    strategy=strategy, side=side, training=training,
                    risk=risk, costs=costs,
                )
                val_stats = performance(validation)
                raw_validation, raw_scan = observe_unfiltered_period(
                    bars, fold.validation_start, fold.validation_end,
                    strategy=strategy, side=side, risk=risk, costs=costs,
                )
                raw_stats = performance(raw_validation)
                # Diagnostic raw strategy outcomes MUST NOT influence admission.
                # Frozen validation admission. The TEST labels never influence this.
                admitted = (
                    len(training) >= risk.min_train_samples
                    and val_stats["trades"] >= risk.min_validation_trades
                    and val_stats["expectancy_net"] is not None
                    and val_stats["expectancy_net"] > 0
                )
                test, test_scan = _observe_period(
                    bars, fold.test_start, fold.test_end,
                    strategy=strategy, side=side, training=training,
                    risk=risk, costs=costs,
                ) if admitted else ([], {
                    "examined": 0, "signals": 0, "missing_training": 0,
                    "rejected_nonpositive": 0, "rejected_uncertainty": 0,
                    "unpriceable_gaps": 0, "executed_proxy": 0,
                    "status": "NOT_EVALUATED_VALIDATION_GATE",
                })
                rows.append({
                    "fold": n,
                    "split": fold.as_dict(),
                    "symbol": symbol,
                    "asset_type": asset_type,
                    "instrument_type": instrument_type,
                    "reference_only": proxy,
                    "strategy": strategy,
                    "side": side,
                    "horizon_minutes": risk.horizon_minutes,
                    "stop_fraction": risk.stop_fraction,
                    "take_fraction": risk.take_fraction,
                    "cost_source": costs.source,
                    "round_trip_cost": costs.round_trip,
                    "training_samples": len(training),
                    "max_train_label_exit_index": max((v[2] for v in training), default=None),
                    "validation": val_stats,
                    "validation_scan": val_scan,
                    "unfiltered_validation": raw_stats,
                    "unfiltered_validation_scan": raw_scan,
                    "unfiltered_validation_trades": raw_validation,
                    "admitted_before_test": admitted,
                    "test": performance(test) if admitted else None,
                    "test_scan": test_scan if admitted else None,
                    "validation_trades": validation,
                    "test_trades": test,
                    "model": "strategy_side_conditioned_knn_frozen_train",
                    "execution": "signal_close_i_next_open_i_plus_1_conservative_intrabar",
                    "mode": "RESEARCH_ONLY",
                })
    return {
        "version": "3.6-research-2",
        "mode": "RESEARCH_ONLY",
        "symbol": symbol,
        "asset_type": asset_type,
        "instrument_type": instrument_type,
        "reference_only": proxy,
        "data_candles": len(bars),
        "first_timestamp": bars[0].timestamp,
        "last_timestamp": bars[-1].timestamp,
        "costs": {**asdict(costs), "round_trip": costs.round_trip},
        "risk": asdict(risk),
        "folds": [fold.as_dict() for fold in sections],
        "results": rows,
        "warning": (
            "Historical counterfactual only; not PLN PnL, live track record, "
            "trade permission or deployable broker execution. Unfiltered "
            "VALIDATION is a descriptive counterfactual, not an admission rule; "
            "its independent non-overlap sequence is not a paired trade-by-trade "
            "comparison. No unadmitted TEST outcome is inspected. Cost assumptions "
            "must be checked against executable market quotes."
        ),
    }
