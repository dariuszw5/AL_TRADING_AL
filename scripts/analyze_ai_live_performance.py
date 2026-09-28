from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path


STATE_PATH = Path("data/live_state/ai_paper.json")


def profit_of(trade):
    return float(trade.get("profit") or 0.0)


def stats(rows):
    count = len(rows)
    total = sum(profit_of(row) for row in rows)
    wins = sum(1 for row in rows if profit_of(row) > 0)
    losses = sum(1 for row in rows if profit_of(row) < 0)
    gross_win = sum(profit_of(row) for row in rows if profit_of(row) > 0)
    gross_loss = abs(
        sum(profit_of(row) for row in rows if profit_of(row) < 0)
    )
    profit_factor = (
        float("inf")
        if gross_loss == 0 and gross_win > 0
        else gross_win / gross_loss
        if gross_loss > 0
        else 0.0
    )
    return {
        "count": count,
        "wins": wins,
        "losses": losses,
        "win_rate": wins / count * 100.0 if count else 0.0,
        "pnl": total,
        "expectancy": total / count if count else 0.0,
        "profit_factor": profit_factor,
    }


def print_stats(name, rows):
    value = stats(rows)
    pf_value = value["profit_factor"]
    pf_text = "INF" if pf_value == float("inf") else f"{pf_value:.3f}"
    print(
        f"{name:<28}"
        f" trades={value['count']:>3}"
        f" | W/L={value['wins']:>2}/{value['losses']:<2}"
        f" | WR={value['win_rate']:>6.2f}%"
        f" | PnL={value['pnl']:>9.3f}"
        f" | EXP={value['expectancy']:>8.3f}"
        f" | PF={pf_text}"
    )


def grouped(trades, key):
    result = defaultdict(list)
    for trade in trades:
        result[str(trade.get(key) or "UNKNOWN")].append(trade)
    return result


def main():
    state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    trades = list(state.get("trades") or [])

    funded = float(state.get("funded_capital") or 0.0)
    balance = float(state.get("balance") or 0.0)
    equity = float(state.get("equity") or 0.0)
    realized = float(state.get("realized_pnl") or 0.0)
    unrealized = float(state.get("unrealized_pnl") or 0.0)
    swept = float(state.get("profit_swept") or 0.0)
    daily_loss = float(state.get("daily_loss") or 0.0)

    trade_sum = sum(profit_of(trade) for trade in trades)
    economic_value = equity + swept
    economic_pnl = economic_value - funded
    state_pnl = realized + unrealized
    accounting_gap = economic_pnl - state_pnl

    print("=" * 112)
    print("AI LIVE PERFORMANCE / ACCOUNTING")
    print("=" * 112)
    print("model                 :", state.get("model"))
    print("funded capital        :", round(funded, 6))
    print("free balance          :", round(balance, 6))
    print("equity                :", round(equity, 6))
    print("realized pnl (state)  :", round(realized, 6))
    print("unrealized pnl        :", round(unrealized, 6))
    print("profit swept          :", round(swept, 6))
    print("daily loss            :", round(daily_loss, 6))
    print("halted                :", state.get("halted"))
    print("trades                :", len(trades))
    print("sum trade profits     :", round(trade_sum, 6))
    print("equity + swept        :", round(economic_value, 6))
    print("economic pnl          :", round(economic_pnl, 6))
    print("state pnl             :", round(state_pnl, 6))
    print("ACCOUNTING GAP        :", round(accounting_gap, 6))

    if abs(accounting_gap) > 0.01:
        print()
        print(
            "WARNING: equity + swept - funded does not match "
            "realized_pnl + unrealized_pnl."
        )
        print(
            "This indicates a state/accounting migration/reset inconsistency "
            "and must be investigated before strategy tuning."
        )

    print()
    print("=== OVERALL ===")
    print_stats("ALL", trades)

    for title, key in (
        ("STRATEGY", "strategy"),
        ("SIDE", "side"),
        ("EXIT REASON", "reason"),
        ("SYMBOL", "symbol"),
    ):
        print()
        print(f"=== {title} ===")
        rows_by_key = grouped(trades, key)
        ordered = sorted(
            rows_by_key.items(),
            key=lambda item: stats(item[1])["pnl"],
        )
        for name, rows in ordered:
            print_stats(name, rows)

    print()
    print("=== STRATEGY LEARNING ===")
    for strategy, value in (state.get("strategy_learning") or {}).items():
        count = int(value.get("trades") or 0)
        wins = int(value.get("wins") or 0)
        total_return = float(value.get("total_return") or 0.0)
        mean_return = total_return / count if count else 0.0
        print(
            f"{strategy:<20}"
            f" trades={count:>3}"
            f" | wins={wins:>3}"
            f" | WR={wins / count * 100 if count else 0:>6.2f}%"
            f" | mean_return={mean_return:>9.6f}"
        )

    print()
    print("=== OPEN POSITIONS ===")
    positions = state.get("positions") or {}
    if not positions:
        print("NONE")
    for symbol, position in positions.items():
        print(
            symbol,
            "|", position.get("side"),
            "|", position.get("strategy"),
            "| allocation:", round(
                float(position.get("allocation_pln") or 0.0), 4
            ),
            "| pnl:", round(
                float(position.get("unrealized_pnl") or 0.0), 4
            ),
            "| score:", position.get("score"),
            "| exploratory:", position.get("exploratory"),
        )

    print()
    print("=== PENDING ===")
    pending = state.get("pending") or []
    if not pending:
        print("NONE")
    for row in pending:
        print(
            row.get("symbol"),
            "|", row.get("side"),
            "|", row.get("strategy"),
            "| score:", row.get("score"),
            "| exploratory:", row.get("exploratory"),
        )

    print()
    print("=== LAST 30 TRADES ===")
    for index, trade in enumerate(trades[-30:], 1):
        print(
            f"{index:>2}.",
            trade.get("symbol"),
            "|", trade.get("side"),
            "|", trade.get("strategy"),
            "|", trade.get("reason"),
            "| pnl:", round(profit_of(trade), 4),
            "| return:", round(
                float(trade.get("return_fraction") or 0.0) * 100.0,
                4,
            ),
            "%",
            "| exploratory:", trade.get("exploratory"),
        )

    print()
    print("=" * 112)


if __name__ == "__main__":
    main()
