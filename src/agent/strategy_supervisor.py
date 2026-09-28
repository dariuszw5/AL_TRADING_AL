"""Live meta-controller that supervises strategy quality.

The supervisor does not predict prices. It evaluates the agent's own closed
paper trades and can prevent a weak strategy from opening more positions.
A paused strategy may only return through a strongly validated probationary
signal, which is sized smaller than a normal trade.
"""
from __future__ import annotations

from statistics import mean

RECENT_TRADE_WINDOW = 30
MIN_STRATEGY_TRADES = 5
PAUSE_PROFIT_FACTOR = 0.75
PAUSE_STOP_LOSS_RATE = 0.60
PAUSE_CONSECUTIVE_LOSSES = 4
PROBATION_SCORE = 0.0030
PROBATION_VALIDATION_TRADES = 6
PROBATION_VALIDATION_MEAN = 0.0010
PROBATION_EXPOSURE = 0.03


def _return_fraction(trade):
    return float(trade.get("return_fraction") or 0.0)


def _snapshot(rows):
    rows = list(rows)[-RECENT_TRADE_WINDOW:]
    count = len(rows)
    returns = [_return_fraction(row) for row in rows]
    wins = [value for value in returns if value > 0]
    losses = [value for value in returns if value < 0]
    gross_win = sum(wins)
    gross_loss = abs(sum(losses))

    if gross_loss > 0:
        profit_factor = gross_win / gross_loss
    elif gross_win > 0:
        profit_factor = float("inf")
    else:
        profit_factor = 0.0

    stop_losses = sum(
        1
        for row in rows
        if row.get("reason") in {"STOP_LOSS", "STOP_GAP"}
    )

    consecutive_losses = 0
    for row in reversed(rows):
        if _return_fraction(row) < 0:
            consecutive_losses += 1
        else:
            break

    avg_return = mean(returns) if returns else 0.0
    win_rate = len(wins) / count if count else 0.0
    stop_loss_rate = stop_losses / count if count else 0.0

    if count < MIN_STRATEGY_TRADES:
        status = "LEARNING"
        reason = (
            f"Za mało transakcji live: {count}/{MIN_STRATEGY_TRADES}. "
            "Strategia pozostaje pod obserwacją."
        )
    elif avg_return < 0 and (
        profit_factor < PAUSE_PROFIT_FACTOR
        or stop_loss_rate >= PAUSE_STOP_LOSS_RATE
        or consecutive_losses >= PAUSE_CONSECUTIVE_LOSSES
    ):
        status = "PAUSED"
        reason = (
            "Ujemna skuteczność live przekroczyła limit bezpieczeństwa. "
            "Nowe zwykłe wejścia są zablokowane."
        )
    elif avg_return <= 0 or profit_factor < 1.0:
        status = "WATCH"
        reason = (
            "Wynik live nie potwierdza jeszcze dodatniej przewagi. "
            "Dozwolone są tylko mocniej potwierdzone wejścia."
        )
    else:
        status = "ACTIVE"
        reason = "Wyniki live nie uruchamiają blokady strategii."

    return {
        "status": status,
        "reason": reason,
        "trades": count,
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": win_rate,
        "mean_return": avg_return,
        "profit_factor": profit_factor,
        "stop_loss_rate": stop_loss_rate,
        "consecutive_losses": consecutive_losses,
    }


def build_strategy_supervisor(trades, strategies):
    trades = list(trades or [])
    result = {}

    for strategy in strategies:
        strategy_rows = [
            row for row in trades if row.get("strategy") == strategy
        ]
        snapshot = _snapshot(strategy_rows)
        snapshot["sides"] = {
            side: _snapshot(
                row for row in strategy_rows if row.get("side") == side
            )
            for side in ("LONG", "SHORT")
        }
        result[strategy] = snapshot

    statuses = [row["status"] for row in result.values()]
    if "PAUSED" in statuses:
        overall = "GUARDED"
    elif "WATCH" in statuses:
        overall = "WATCH"
    elif statuses and all(status == "ACTIVE" for status in statuses):
        overall = "ACTIVE"
    else:
        overall = "LEARNING"

    return {
        "version": 1,
        "overall_status": overall,
        "recent_trade_window": RECENT_TRADE_WINDOW,
        "min_strategy_trades": MIN_STRATEGY_TRADES,
        "strategies": result,
        "rules": {
            "pause_profit_factor_below": PAUSE_PROFIT_FACTOR,
            "pause_stop_loss_rate_at_or_above": PAUSE_STOP_LOSS_RATE,
            "pause_consecutive_losses_at_or_above": PAUSE_CONSECUTIVE_LOSSES,
            "probation_score_at_or_above": PROBATION_SCORE,
            "probation_validation_trades_at_or_above": (
                PROBATION_VALIDATION_TRADES
            ),
            "probation_validation_mean_at_or_above": (
                PROBATION_VALIDATION_MEAN
            ),
            "probation_exposure": PROBATION_EXPOSURE,
        },
    }


def supervise_candidate(row, supervisor):
    """Apply live strategy health to one already-ranked candidate."""
    strategy = row.get("strategy")
    health = (
        (supervisor.get("strategies") or {}).get(strategy)
        or {"status": "LEARNING", "reason": "Brak historii live."}
    )
    status = health.get("status", "LEARNING")

    row["supervisor_status"] = status
    row["supervisor_reason"] = health.get("reason")
    row["supervisor_probation"] = False
    row["supervisor_exposure"] = None

    if not row.get("eligible"):
        return row

    if status == "PAUSED":
        validation_mean = row.get("validation_mean")
        recovery = bool(
            row.get("validated")
            and int(row.get("validation_trades") or 0)
            >= PROBATION_VALIDATION_TRADES
            and validation_mean is not None
            and float(validation_mean) >= PROBATION_VALIDATION_MEAN
            and float(row.get("score") or 0.0) >= PROBATION_SCORE
        )

        if not recovery:
            row["eligible"] = False
            row["eligibility_reason"] = "STRATEGY_SUPERVISOR_PAUSED"
            return row

        row["supervisor_probation"] = True
        row["supervisor_exposure"] = PROBATION_EXPOSURE
        row["eligibility_reason"] = "STRATEGY_SUPERVISOR_PROBATION"
        return row

    if status == "WATCH" and row.get("exploratory"):
        row["eligible"] = False
        row["eligibility_reason"] = "STRATEGY_SUPERVISOR_WATCH_NO_EXPLORATION"

    return row
