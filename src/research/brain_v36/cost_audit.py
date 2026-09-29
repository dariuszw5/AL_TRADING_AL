"""Validation-only cost decomposition of ALREADY-SAVED Brain v3.6 reports.

No market fetches, no recomputation of decisions, no optimization and no
inspection of held-out TEST outcomes. One row = one instrument/strategy/
direction/horizon/fold. Overlapping expanding folds are NOT independent.
"""
from __future__ import annotations

from math import isclose, isfinite
from statistics import mean


def _metrics(trades: list[dict], *, side: str, expected_cost: float) -> dict:
    if side not in ("LONG", "SHORT"):
        raise ValueError("Invalid trade side")
    if not trades:
        return {
            "trades": 0,
            "mean_gross": None,
            "mean_net": None,
            "break_even_round_trip_cost": None,
            "gross_wins": 0,
            "net_wins": 0,
            "cost_effect": "NO_SAMPLE",
        }
    gross_returns = []
    net_returns = []
    direction = 1 if side == "LONG" else -1
    for trade in trades:
        entry = float(trade["entry_mid"])
        exit_price = float(trade["exit_mid"])
        net = float(trade["return_fraction"])
        cost = float(trade["round_trip_cost"])
        if not all(isfinite(v) for v in (entry, exit_price, net, cost)):
            raise ValueError("Nonfinite trade observation")
        if min(entry, exit_price) <= 0 or not isclose(
            cost, expected_cost, abs_tol=1e-12, rel_tol=1e-10
        ):
            raise ValueError("Invalid entry/exit or inconsistent cost assumptions")
        gross = direction * (exit_price / entry - 1)
        if not isclose(
            net + cost, gross, abs_tol=1e-12, rel_tol=1e-9
        ):
            raise ValueError("Reported net return does not reconcile with execution prices")
        gross_returns.append(gross)
        net_returns.append(net)
    gross_expectancy = mean(gross_returns)
    net_expectancy = mean(net_returns)
    if gross_expectancy <= 0:
        effect = "NONPOSITIVE_GROSS_EDGE"
    elif net_expectancy <= 0:
        effect = "COST_ERASES_GROSS_EDGE"
    else:
        effect = "POSITIVE_NET_IN_VALIDATION"
    return {
        "trades": len(trades),
        "mean_gross": gross_expectancy,
        "mean_net": net_expectancy,
        # Maximum round-trip expense that leaves expectancy == 0, NOT
        # a measured quote or recommendation to change the cost profile.
        "break_even_round_trip_cost": gross_expectancy,
        "gross_wins": sum(v > 0 for v in gross_returns),
        "net_wins": sum(v > 0 for v in net_returns),
        "cost_effect": effect,
    }


def analyze_sealed_validation(payload: dict) -> list[dict]:
    """Fail closed unless EVERY run was explicitly validation-only.

    This deliberately NEVER computes or exposes held-out TEST performance.
    """
    if payload.get("mode") != "RESEARCH_ONLY" or not payload.get("runs"):
        raise ValueError("A nonempty RESEARCH_ONLY report is required")
    result = []
    for run in payload["runs"]:
        if run.get("mode") != "RESEARCH_ONLY" or run.get("evaluate_test") is not False:
            raise ValueError("Refusing a report that may have evaluated held-out TEST")
        if run.get("reference_only") and run.get("instrument_type") is None:
            raise ValueError("Reference-only instrument metadata missing")
        base_cost = float(run["costs"]["round_trip"])
        if not isfinite(base_cost) or not 0 <= base_cost < 1:
            raise ValueError("Invalid report round-trip cost")
        for record in run["results"]:
            if (record.get("test") is not None
                    or record.get("test_scan") is not None
                    or record.get("test_trades")
                    or record.get("test_status") not in (
                        "SEALED_VALIDATION_ONLY", "NOT_EVALUATED_VALIDATION_GATE"
                    )):
                raise ValueError("Held-out TEST is not sealed; refusing audit")
            row_cost = float(record["round_trip_cost"])
            if not isclose(row_cost, base_cost, abs_tol=1e-12, rel_tol=1e-10):
                raise ValueError("Cost differs between fold and run")
            side = record["side"]
            raw = _metrics(record["unfiltered_validation_trades"], side=side,
                           expected_cost=base_cost)
            filtered = _metrics(record["validation_trades"], side=side,
                                expected_cost=base_cost)
            if raw["trades"] != record["unfiltered_validation"]["trades"]:
                raise ValueError("Raw validation count differs from recorded statistics")
            if filtered["trades"] != record["validation"]["trades"]:
                raise ValueError("Filtered validation count differs from recorded statistics")
            if raw["mean_net"] is not None and not isclose(
                raw["mean_net"], record["unfiltered_validation"]["expectancy_net"],
                abs_tol=1e-12, rel_tol=1e-10,
            ):
                raise ValueError("Raw validation expectancy does not reconcile")
            if filtered["mean_net"] is not None and not isclose(
                filtered["mean_net"], record["validation"]["expectancy_net"],
                abs_tol=1e-12, rel_tol=1e-10,
            ):
                raise ValueError("Filtered validation expectancy does not reconcile")
            result.append({
                "symbol": record["symbol"],
                "asset_type": record["asset_type"],
                "fold": record["fold"],
                "strategy": record["strategy"],
                "side": side,
                "horizon_minutes": record["horizon_minutes"],
                "bar_minutes": record.get("bar_minutes", run.get("bar_minutes", 1)),
                "cost_source": record["cost_source"],
                "assumed_round_trip_cost": base_cost,
                "raw_signals": record["unfiltered_validation_scan"]["signals"],
                "filtered_signals": record["validation_scan"]["signals"],
                "raw_trades": raw["trades"],
                "raw_mean_gross": raw["mean_gross"],
                "raw_mean_net": raw["mean_net"],
                "raw_break_even_cost": raw["break_even_round_trip_cost"],
                "raw_gross_wins": raw["gross_wins"],
                "raw_net_wins": raw["net_wins"],
                "raw_cost_effect": raw["cost_effect"],
                "filtered_trades": filtered["trades"],
                "filtered_mean_gross": filtered["mean_gross"],
                "filtered_mean_net": filtered["mean_net"],
                "filtered_break_even_cost": filtered["break_even_round_trip_cost"],
                "filtered_gross_wins": filtered["gross_wins"],
                "filtered_net_wins": filtered["net_wins"],
                "filtered_cost_effect": filtered["cost_effect"],
                "admitted_before_test": record["admitted_before_test"],
                "test_status": record["test_status"],
            })
    if not result:
        raise ValueError("No eligible sealed-validation audit rows")
    return result
