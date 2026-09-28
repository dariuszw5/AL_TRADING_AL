"""Conservative, directional adviser for already-eligible paper candidates.

Counterfactual observations are not a live track record. This adviser only
breaks ties/changes ranking among candidates that passed all existing model,
validation, Supervisor and risk gates. Never raises eligibility or position
exposure and never writes to the paper balance or realized learning counters.
"""
from __future__ import annotations

from collections import Counter
from math import isfinite
from statistics import mean

SHADOW_RECENT_WINDOW = 48
SHADOW_MIN_TRADES = 24
SHADOW_MIN_SYMBOLS = 3
SHADOW_MIN_HALF_TRADES = 12
SHADOW_MIN_EDGE_AFTER_COSTS = 0.0002
SHADOW_MIN_HALF_PROFIT_FACTOR = 1.10
SHADOW_MAX_RANKING_BONUS = 0.00075


def _profit_factor(values: list[float]) -> float | None:
    win = sum(value for value in values if value > 0)
    loss = -sum(value for value in values if value < 0)
    if loss == 0:
        # Null in JSON represents an undefined ratio (e.g. no losses).
        return None
    return win / loss


def assess_shadow_evidence(shadow: dict, strategy: str, side: str) -> dict:
    """Inspect *recent* independent forward paper-proxy observations only.

    The aggregate lifetime counters in shadow['learning'] are for reporting;
    advisory confidence uses the recent bounded trades to avoid making a
    decision on stale evidence from a past market regime.
    """
    relevant = []
    dedup = set()
    for trade in reversed(shadow.get("trades") or []):
        if trade.get("counterfactual") is not True:
            continue
        if trade.get("strategy") != strategy or trade.get("side") != side:
            continue
        symbol = str(trade.get("symbol") or "")
        timestamp = trade.get("signal_timestamp")
        if not symbol or timestamp is None:
            continue
        key = (symbol, timestamp)
        if key in dedup:
            continue
        try:
            value = float(trade["return_fraction"])
            exit_ts = int(trade["exit_timestamp"])
        except (KeyError, TypeError, ValueError, OverflowError):
            continue
        if not isfinite(value):
            continue
        dedup.add(key)
        relevant.append((exit_ts, symbol, value))
        if len(relevant) >= SHADOW_RECENT_WINDOW:
            break

    relevant.sort(key=lambda item: item[0])
    count = len(relevant)
    values = [entry[2] for entry in relevant]
    symbols = Counter(entry[1] for entry in relevant)
    average = mean(values) if values else None
    result = {
        "strategy": strategy,
        "side": side,
        "source": "OBSERVATION_ONLY",
        "samples": count,
        "distinct_symbols": len(symbols),
        "mean_after_costs": average,
        "profit_factor": _profit_factor(values),
        "status": "INSUFFICIENT_SAMPLES",
        "bonus": 0.0,
    }

    if count < SHADOW_MIN_TRADES:
        return result

    if (
        len(symbols) < SHADOW_MIN_SYMBOLS
        or max(symbols.values(), default=0) / count > 0.60
    ):
        result["status"] = "CONCENTRATED_SAMPLE"
        return result

    midpoint = count // 2
    older = relevant[:midpoint]
    newer = relevant[midpoint:]
    if (
        len(older) < SHADOW_MIN_HALF_TRADES
        or len(newer) < SHADOW_MIN_HALF_TRADES
    ):
        return result

    # Separate chronological windows, avoiding a single lucky recent streak.
    for window in (older, newer):
        returns = [entry[2] for entry in window]
        pf = _profit_factor(returns)
        if (
            mean(returns) <= 0.0
            or (pf is not None and pf < SHADOW_MIN_HALF_PROFIT_FACTOR)
        ):
            result["status"] = "INCONSISTENT_WINDOWS"
            return result

    if average is None or average < SHADOW_MIN_EDGE_AFTER_COSTS:
        result["status"] = "INSUFFICIENT_NET_EDGE"
        return result

    bonus = min(
        SHADOW_MAX_RANKING_BONUS,
        0.25 * average,
    ) * min(1.0, count / SHADOW_RECENT_WINDOW)

    result["status"] = "SHADOW_CONFIRMED_FOR_RANKING"
    result["bonus"] = bonus
    return result


def apply_shadow_advisor(rows: list[dict], shadow: dict) -> dict[str, dict]:
    """Annotate ranking rows without changing their base score or gates."""
    assessments: dict[str, dict] = {}
    for row in rows:
        strategy = str(row.get("strategy") or "")
        side = str(row.get("side") or "")
        key = strategy + "|" + side
        if key not in assessments:
            assessments[key] = assess_shadow_evidence(shadow, strategy, side)

        assessment = assessments[key]
        raw_score = row.get("score")
        original = float(raw_score) if raw_score is not None else None
        # The entire bonus applies ONLY to previously approved candidates.
        bonus = (
            float(assessment["bonus"])
            if row.get("eligible") and original is not None
            else 0.0
        )
        row["shadow_selection_score"] = (
            original + bonus if original is not None else None
        )
        row["shadow_selection_bonus"] = bonus
        row["shadow_advisor"] = assessment
    return assessments
