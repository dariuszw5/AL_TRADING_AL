"""Bounded, observation-only cross-market shadow ledger.

Independent of funded PLN, brokerage positions, pending orders and live
strategy-learning counters. Uses only already closed candles. Shadow outcomes
are counterfactual labels, never actual paper orders or realized PnL.
"""
from __future__ import annotations

from math import isfinite

SHADOW_OPEN_LIMIT = 200
SHADOW_HISTORY_LIMIT = 500
SHADOW_SEEN_LIMIT = 5000


def empty_shadow_ledger() -> dict:
    return {
        "version": 1,
        "pending": {},
        "positions": {},
        "trades": [],
        "seen": {},
        "learning": {},
        "expired_signals": 0,
        "data_gaps": 0,
        "capacity_skips": 0,
    }


def update_shadow_ledger(
    account: dict,
    fresh: dict,
    rows: list[dict],
    *,
    minute: int,
    horizon: int,
    exit_price,
    net_return,
) -> dict:
    """Advance observations and register current signals without trading.

    A signal is recorded at its closed candle. A shadow entry is established
    only when the immediately following candle is *closed* and observable;
    entry is that candle's open, with conservative intrabar SL/TP handling
    delegated to the same exit_price function as the paper backtest.
    """
    shadow = account.setdefault("shadow", empty_shadow_ledger())
    default = empty_shadow_ledger()
    for name, value in default.items():
        shadow.setdefault(name, value)

    pending = shadow["pending"]
    positions = shadow["positions"]
    seen = shadow["seen"]

    # Resolve old pending signals; never jump over a missing next candle.
    for key, item in list(pending.items()):
        bars = fresh.get(item["symbol"]) or []
        signal_timestamp = int(item["signal_timestamp"])
        next_candle = next(
            (c for c in bars if c.timestamp > signal_timestamp), None
        )
        if next_candle is None:
            continue
        pending.pop(key)
        if next_candle.timestamp != signal_timestamp + minute:
            shadow["expired_signals"] += 1
            continue
        entry = float(next_candle.open)
        if not isfinite(entry) or entry <= 0:
            shadow["expired_signals"] += 1
            continue
        positions[key] = {
            **item,
            "entry": entry,
            "entry_timestamp": int(next_candle.timestamp),
            "last_timestamp": signal_timestamp,
            # Replicate outcome(): candles i+1 ... i+HORIZON.
            "exit_at": signal_timestamp + horizon * minute,
        }

    # Progress shadow positions strictly in chronological order.
    for key, position in list(positions.items()):
        bars = fresh.get(position["symbol"]) or []
        for candle in bars:
            timestamp = int(candle.timestamp)
            if timestamp <= int(position["last_timestamp"]):
                continue
            if timestamp != int(position["last_timestamp"]) + minute:
                positions.pop(key)
                shadow["data_gaps"] += 1
                break

            result = exit_price(
                candle,
                float(position["entry"]),
                str(position["side"]),
                timed_out=timestamp >= int(position["exit_at"]),
            )
            position["last_timestamp"] = timestamp
            if result is None:
                continue

            ret = float(net_return(
                float(position["entry"]), float(result[0]), str(position["side"])
            ))
            if not isfinite(ret):
                positions.pop(key)
                shadow["data_gaps"] += 1
                break
            trade = {
                "symbol": position["symbol"],
                "strategy": position["strategy"],
                "side": position["side"],
                "signal_timestamp": position["signal_timestamp"],
                "entry_timestamp": position["entry_timestamp"],
                "exit_timestamp": timestamp,
                "entry": position["entry"],
                "exit_price": float(result[0]),
                "reason": result[1],
                "return_fraction": ret,
                "eligible_at_signal": position["eligible_at_signal"],
                "supervisor_status_at_signal": position.get(
                    "supervisor_status_at_signal"
                ),
                "counterfactual": True,
            }
            shadow["trades"] = (
                shadow["trades"] + [trade]
            )[-SHADOW_HISTORY_LIMIT:]
            learning_key = str(position["strategy"]) + "|" + str(position["side"])
            bucket = shadow["learning"].setdefault(
                learning_key,
                {
                    "trades": 0,
                    "wins": 0,
                    "total_return": 0.0,
                    "gross_win": 0.0,
                    "gross_loss": 0.0,
                },
            )
            bucket["trades"] += 1
            bucket["wins"] += int(ret > 0)
            bucket["total_return"] += ret
            bucket["gross_win"] += max(ret, 0.0)
            bucket["gross_loss"] += min(ret, 0.0)
            positions.pop(key)
            break

    # Shadow signals remain observable even when Supervisor says PAUSED or
    # model validation rejects them. One non-overlapping candidate per
    # (symbol, strategy, side); repeated cycles never duplicate a candle.
    for row in rows:
        if not row.get("live_signal"):
            continue
        symbol = str(row.get("symbol") or "")
        strategy = str(row.get("strategy") or "")
        side = str(row.get("side") or "")
        if not symbol or not strategy or side not in {"LONG", "SHORT"}:
            continue
        bars = fresh.get(symbol) or []
        if not bars:
            continue
        timestamp = int(bars[-1].timestamp)
        key = "|".join((symbol, strategy, side))
        if timestamp <= int(seen.get(key, -1)):
            continue
        seen[key] = timestamp
        if key in pending or key in positions:
            continue
        if len(pending) + len(positions) >= SHADOW_OPEN_LIMIT:
            shadow["capacity_skips"] += 1
            continue
        pending[key] = {
            "symbol": symbol,
            "strategy": strategy,
            "side": side,
            "signal_timestamp": timestamp,
            "eligible_at_signal": bool(row.get("eligible")),
            "supervisor_status_at_signal": row.get("supervisor_status"),
        }

    if len(seen) > SHADOW_SEEN_LIMIT:
        newest = sorted(
            seen.items(), key=lambda item: item[1], reverse=True
        )[:SHADOW_SEEN_LIMIT]
        shadow["seen"] = dict(newest)

    shadow["summary"] = {
        "pending": len(shadow["pending"]),
        "open": len(shadow["positions"]),
        "stored_trades": len(shadow["trades"]),
        "completed_total": sum(
            bucket["trades"] for bucket in shadow["learning"].values()
        ),
        "expired_signals": shadow["expired_signals"],
        "data_gaps": shadow["data_gaps"],
        "capacity_skips": shadow["capacity_skips"],
        "observation_only": True,
    }
    return shadow
