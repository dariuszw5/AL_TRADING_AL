"""Brain v3.6 Phase 9B+ research/shadow components.

Research-only. Produces SHADOW_DECISION records and never imports broker/order/funding code.
All decisions are based on closed candles; execution diagnostics use next-bar open and a
conservative stop-first rule when OHLC cannot reveal intrabar ordering.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, time, timezone
from math import isfinite, sqrt
from pathlib import Path
from statistics import mean, median, pstdev
from typing import Iterable, Mapping, Sequence
from zoneinfo import ZoneInfo
import json

from .engine import features as brain_features, signal_side, validate_history

STRATEGIES = ("trend", "mean_reversion", "breakout", "trend_pullback_v1")
SIDES = ("LONG", "SHORT")


def _validate_history_compat(candles: Sequence, bar_minutes: int) -> tuple:
    """Support both pre-interval and interval-aware local Brain v3.6 engines."""
    try:
        return validate_history(candles, bar_minutes=bar_minutes)
    except TypeError as exc:
        if "bar_minutes" not in str(exc):
            raise
        rows = validate_history(candles)
        expected = bar_minutes * 60_000
        if len(rows) > 1 and not any(rows[j].timestamp - rows[j-1].timestamp == expected for j in range(1, len(rows))):
            raise ValueError("No candles at declared bar interval")
        return rows


def _signal_side_compat(strategy: str, candles: Sequence, i: int, bar_minutes: int) -> str | None:
    try:
        return signal_side(strategy, candles, i, bar_minutes)
    except TypeError as exc:
        if "positional" not in str(exc) and "argument" not in str(exc):
            raise
        return signal_side(strategy, candles, i)


@dataclass(frozen=True)
class ShadowCostModel:
    commission_per_side: float
    spread_round_trip: float
    slippage_per_side: float
    overnight_financing_per_day: float = 0.0
    source: str = "UNVERIFIED_RESEARCH_ASSUMPTION"

    def __post_init__(self):
        for name in ("commission_per_side", "spread_round_trip", "slippage_per_side", "overnight_financing_per_day"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) or value < 0:
                raise ValueError(f"{name}: finite non-negative fraction required")
        if not self.source or not isinstance(self.source, str):
            raise ValueError("cost source is required")

    @property
    def round_trip(self) -> float:
        return 2 * self.commission_per_side + self.spread_round_trip + 2 * self.slippage_per_side

    def net_fraction(self, entry: float, exit: float, side: str, holding_minutes: int = 0) -> float:
        if side not in SIDES or min(entry, exit) <= 0:
            raise ValueError("invalid execution input")
        gross = (exit / entry - 1.0) * (1 if side == "LONG" else -1)
        financing = self.overnight_financing_per_day * max(0.0, holding_minutes / 1440.0)
        return gross - self.round_trip - financing


@dataclass(frozen=True)
class SessionProfile:
    timezone_name: str
    open_local: time
    close_local: time
    opening_minutes: int = 90
    closing_minutes: int = 90


US_EQUITY_SESSION = SessionProfile("America/New_York", time(9, 30), time(16, 0))


def session_phase(timestamp_ms: int, profile: SessionProfile | None) -> str:
    if profile is None:
        return "ALWAYS_OPEN"
    dt = datetime.fromtimestamp(timestamp_ms / 1000, timezone.utc).astimezone(ZoneInfo(profile.timezone_name))
    if dt.weekday() >= 5:
        return "CLOSED"
    local = dt.time().replace(tzinfo=None)
    if local < profile.open_local:
        return "PRE_OPEN"
    if local >= profile.close_local:
        return "CLOSED"
    minute = dt.hour * 60 + dt.minute
    open_m = profile.open_local.hour * 60 + profile.open_local.minute
    close_m = profile.close_local.hour * 60 + profile.close_local.minute
    if minute < open_m + profile.opening_minutes:
        return "OPENING"
    if minute >= close_m - profile.closing_minutes:
        return "CLOSING"
    return "MID_SESSION"


def _sma(values: Sequence[float], n: int) -> float:
    if len(values) < n:
        raise ValueError("insufficient SMA history")
    return mean(values[-n:])


def _atr(candles: Sequence, period: int = 14) -> float:
    if len(candles) < period + 1:
        raise ValueError("insufficient ATR history")
    rows = candles[-period - 1 :]
    vals = []
    for a, b in zip(rows, rows[1:]):
        vals.append(max(b.high - b.low, abs(b.high - a.close), abs(b.low - a.close)))
    return mean(vals)


def regime(candles: Sequence, i: int) -> str:
    if i < 50:
        return "INSUFFICIENT_HISTORY"
    closes = [float(x.close) for x in candles[: i + 1]]
    s20, s50 = _sma(closes, 20), _sma(closes, 50)
    returns = [b / a - 1 for a, b in zip(closes[-21:-1], closes[-20:]) if a > 0]
    vol = pstdev(returns) if len(returns) > 1 else 0.0
    if vol >= 0.02:
        return "HIGH_VOLATILITY"
    gap = abs(s20 / s50 - 1)
    if gap < 0.0025:
        return "RANGE"
    return "TREND_UP" if s20 > s50 else "TREND_DOWN"


def trend_pullback_signal(candles: Sequence, i: int) -> dict | None:
    """Explainable long-only hypothesis from the attached prototype.

    Close(i) must be above SMA50>SMA200, a recent close must have pulled back to
    within 1% of SMA50, and close(i) must break the prior bar high. Stop uses the
    lower of recent swing-low or 1.5 ATR below signal close; target is 2R.
    """
    if i < 201:
        return None
    window = candles[: i + 1]
    closes = [float(b.close) for b in window]
    price = closes[-1]
    s50, s200 = _sma(closes, 50), _sma(closes, 200)
    recent_low = min(float(b.low) for b in window[-6:-1])
    pullback = min(closes[-6:-1]) <= s50 * 1.01
    breakout = price > float(window[-2].high)
    if not (price > s50 > s200 and pullback and breakout and recent_low < price):
        return None
    stop = min(recent_low, price - 1.5 * _atr(window))
    risk = price - stop
    if risk <= 0:
        return None
    return {"side": "LONG", "signal_price": price, "stop": stop, "target": price + 2 * risk,
            "rationale": "price>SMA50>SMA200; pullback_to_SMA50; breakout"}


def strategy_signal(strategy: str, candles: Sequence, i: int, bar_minutes: int) -> dict | None:
    if strategy == "trend_pullback_v1":
        return trend_pullback_signal(candles, i)
    side = _signal_side_compat(strategy, candles, i, bar_minutes)
    if side is None:
        return None
    price = float(candles[i].close)
    atr = _atr(candles[: i + 1]) if i >= 14 else price * 0.01
    risk = max(price * 0.012, 1.5 * atr)
    stop = price - risk if side == "LONG" else price + risk
    target = price + 2 * risk if side == "LONG" else price - 2 * risk
    return {"side": side, "signal_price": price, "stop": stop, "target": target,
            "rationale": f"brain_v36_{strategy}_signal"}


def liquidity_context(candles: Sequence, i: int, cost: ShadowCostModel, *, max_round_trip: float = 0.006) -> dict:
    if cost.round_trip > max_round_trip:
        return {"allowed": False, "reason": "COST_TOO_HIGH", "volume_ratio": None, "round_trip_cost": cost.round_trip}
    vols = [float(x.volume) for x in candles[max(0, i - 20): i + 1] if float(x.volume) > 0]
    if len(vols) < 5:
        return {"allowed": True, "reason": "NO_RELIABLE_VOLUME_REFERENCE", "volume_ratio": None,
                "round_trip_cost": cost.round_trip}
    base = median(vols[:-1]) if len(vols) > 1 else vols[0]
    ratio = vols[-1] / base if base > 0 else None
    return {"allowed": ratio is None or ratio >= 0.25,
            "reason": "OK" if ratio is None or ratio >= 0.25 else "LOW_RELATIVE_VOLUME",
            "volume_ratio": ratio, "round_trip_cost": cost.round_trip}


def event_risk_context(timestamp_ms: int, events: Iterable[Mapping] | None) -> dict:
    matched = []
    for event in events or ():
        start, end = int(event.get("start_ms", -1)), int(event.get("end_ms", -1))
        severity = str(event.get("severity", "UNKNOWN")).upper()
        if start <= timestamp_ms <= end:
            matched.append({"name": str(event.get("name", "event")), "severity": severity})
    blocked = any(x["severity"] in {"HIGH", "CRITICAL"} for x in matched)
    return {"blocked": blocked, "events": matched, "status": "BLOCKED" if blocked else "CLEAR"}


def size_position(*, equity: float, entry: float, stop: float, contract_multiplier: float = 1.0,
                  risk_fraction: float = 0.005, max_exposure_fraction: float = 0.15) -> dict:
    if min(equity, entry, contract_multiplier) <= 0 or not 0 < risk_fraction <= 0.05:
        raise ValueError("invalid sizing input")
    distance = abs(entry - stop) * contract_multiplier
    if distance <= 0:
        return {"quantity": 0.0, "risk_budget": equity * risk_fraction, "notional": 0.0}
    q_risk = equity * risk_fraction / distance
    q_exposure = equity * max_exposure_fraction / (entry * contract_multiplier)
    qty = max(0.0, min(q_risk, q_exposure))
    return {"quantity": qty, "risk_budget": equity * risk_fraction,
            "notional": qty * entry * contract_multiplier}




@dataclass(frozen=True)
class KnnSample:
    features: tuple[float, ...]
    net_return: float
    exit_index: int


def knn_prediction(current_features: Sequence[float], samples: Sequence[KnnSample], *,
                   neighbors: int = 12, min_samples: int = 8,
                   uncertainty_penalty: float = 0.35, min_edge: float = 0.0) -> dict:
    """Past-only k-NN admission score for SHADOW decisions.

    The caller must supply only samples whose trades completed before the current
    signal. This function never reads future candles or TEST/holdout data.
    """
    if neighbors < 1 or min_samples < 2 or uncertainty_penalty < 0 or min_edge < 0:
        raise ValueError("invalid k-NN configuration")
    usable = [s for s in samples if len(s.features) == len(current_features)]
    if len(usable) < min_samples:
        return {"available": False, "admitted": False, "reason": "KNN_INSUFFICIENT_HISTORY",
                "samples": len(usable), "expectation": None, "uncertainty": None,
                "conservative_score": None}
    nearest = sorted(
        usable,
        key=lambda row: sum((float(a) - float(b)) ** 2 for a, b in zip(current_features, row.features)),
    )[:neighbors]
    values = [float(row.net_return) for row in nearest]
    expectation = mean(values)
    uncertainty = pstdev(values) if len(values) > 1 else 0.0
    conservative = expectation - uncertainty_penalty * uncertainty
    admitted = expectation > 0 and conservative > min_edge
    return {"available": True, "admitted": admitted,
            "reason": "KNN_ADMITTED" if admitted else "KNN_REJECTED",
            "samples": len(usable), "neighbors": len(nearest),
            "expectation": expectation, "uncertainty": uncertainty,
            "conservative_score": conservative}


@dataclass(frozen=True)
class ShadowDecision:
    action: str
    symbol: str
    strategy: str
    side: str | None
    signal_index: int
    signal_timestamp: int
    regime: str
    session_phase: str
    cost_estimate: float
    reason: str
    rejection_reason: str | None
    entry_reference: float | None
    stop: float | None
    target: float | None
    quantity: float
    mfe: float | None = None
    mae: float | None = None
    outcome: str | None = None

    def as_dict(self) -> dict:
        return asdict(self)


class DecisionJournal:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def append(self, decision: ShadowDecision) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(decision.as_dict(), ensure_ascii=False, sort_keys=True) + "\n")


def shadow_decision(*, symbol: str, asset_type: str, candles: Sequence, i: int, strategy: str,
                    cost: ShadowCostModel, bar_minutes: int = 5, session: SessionProfile | None = None,
                    events: Iterable[Mapping] | None = None, equity: float = 1000.0,
                    contract_multiplier: float = 1.0, knn: Mapping | None = None,
                    require_knn: bool = False) -> ShadowDecision:
    _validate_history_compat(candles[: i + 1], bar_minutes)
    reg = regime(candles, i)
    phase = session_phase(candles[i].timestamp, None if asset_type == "crypto" else session)
    liq = liquidity_context(candles, i, cost)
    evt = event_risk_context(candles[i].timestamp, events)
    sig = strategy_signal(strategy, candles, i, bar_minutes)
    rejection = None
    if sig is None:
        rejection = "NO_SIGNAL"
    elif reg == "HIGH_VOLATILITY":
        rejection = "HIGH_VOLATILITY_REGIME"
    elif phase in {"PRE_OPEN", "CLOSED"}:
        rejection = "SESSION_CLOSED"
    elif not liq["allowed"]:
        rejection = liq["reason"]
    elif evt["blocked"]:
        rejection = "EVENT_RISK"
    elif require_knn and not knn:
        rejection = "KNN_NOT_AVAILABLE"
    elif knn is not None and not bool(knn.get("admitted", False)):
        rejection = str(knn.get("reason") or "KNN_REJECTED")
    if rejection:
        return ShadowDecision("SHADOW_REJECT", symbol, strategy, sig and sig["side"], i,
                              candles[i].timestamp, reg, phase, cost.round_trip,
                              "research gate rejected", rejection,
                              sig and sig["signal_price"], sig and sig["stop"], sig and sig["target"], 0.0)
    sizing = size_position(equity=equity, entry=sig["signal_price"], stop=sig["stop"],
                           contract_multiplier=contract_multiplier)
    if sizing["quantity"] <= 0:
        return ShadowDecision("SHADOW_REJECT", symbol, strategy, sig["side"], i, candles[i].timestamp,
                              reg, phase, cost.round_trip, "risk sizing rejected", "ZERO_SIZE",
                              sig["signal_price"], sig["stop"], sig["target"], 0.0)
    return ShadowDecision("SHADOW_DECISION", symbol, strategy, sig["side"], i, candles[i].timestamp,
                          reg, phase, cost.round_trip, sig["rationale"], None,
                          sig["signal_price"], sig["stop"], sig["target"], sizing["quantity"])


def conservative_outcome(candles: Sequence, decision: ShadowDecision, *, cost: ShadowCostModel,
                         bar_minutes: int = 5, max_holding_bars: int = 12) -> dict | None:
    """Signal at close(i), fill at open(i+1), stop wins ambiguous bars."""
    if decision.action != "SHADOW_DECISION" or decision.side not in SIDES:
        return None
    i = decision.signal_index
    if i + 1 >= len(candles):
        return None
    entry = float(candles[i + 1].open)
    signal_risk = abs(float(decision.entry_reference) - float(decision.stop))
    if signal_risk <= 0:
        return None
    if decision.side == "LONG":
        stop, target = float(decision.stop), entry + 2 * max(entry - float(decision.stop), signal_risk)
    else:
        stop, target = float(decision.stop), entry - 2 * max(float(decision.stop) - entry, signal_risk)
    mfe = mae = 0.0
    final_j = min(len(candles) - 1, i + max_holding_bars)
    reason, exit_price = "TIME_EXIT", float(candles[final_j].close)
    for j in range(i + 1, final_j + 1):
        bar = candles[j]
        if decision.side == "LONG":
            mfe = max(mfe, bar.high / entry - 1)
            mae = min(mae, bar.low / entry - 1)
            if bar.low <= stop:
                reason, exit_price, final_j = "STOP_LOSS", stop, j; break
            if bar.high >= target:
                reason, exit_price, final_j = "TAKE_PROFIT", target, j; break
        else:
            mfe = max(mfe, entry / bar.low - 1)
            mae = min(mae, entry / bar.high - 1)
            if bar.high >= stop:
                reason, exit_price, final_j = "STOP_LOSS", stop, j; break
            if bar.low <= target:
                reason, exit_price, final_j = "TAKE_PROFIT", target, j; break
    holding_minutes = max(0, final_j - (i + 1)) * bar_minutes
    return {"entry": entry, "exit": exit_price, "reason": reason, "exit_index": final_j,
            "mfe": mfe, "mae": mae,
            "net_return": cost.net_fraction(entry, exit_price, decision.side, holding_minutes)}
