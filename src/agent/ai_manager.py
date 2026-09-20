"""Autonomous cross-market paper broker.

Real market data, virtual PLN only. No broker connector, exchange API key or
real-money order path exists in this module.

The account can hold several independent paper positions at once. Funding is
received only through user-confirmed virtual PLN events in ai_control.json.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timezone
import json
from math import isfinite, sqrt
from pathlib import Path
from statistics import mean, pstdev
from time import time
from uuid import uuid4

from src.agent.live_state_store import LiveStateStore
from src.agent.strategy_supervisor import (
    build_strategy_supervisor,
    supervise_candidate,
)
from src.data.assets import SUPPORTED_ASSETS
from src.data.data_provider import DataProvider

MINUTE = 60_000
HORIZON = 15
FEE = 0.0004
SLIPPAGE = 0.0005
PER_POSITION_EXPOSURE = 0.15
EXPLORATION_POSITION_EXPOSURE = 0.05
MAX_TOTAL_EXPOSURE = 0.75
MAX_OPEN_POSITIONS = 5
MAX_EXPLORATORY_POSITIONS = 1
STOP = 0.012
TAKE = 0.024
STRATEGIES = ("trend", "mean_reversion", "breakout")
SIDES = ("LONG", "SHORT")
LEARNING_WEIGHT = 0.15
MAX_DRAWDOWN = 0.08
MAX_DAILY_LOSS_PCT = 0.10
MIN_VALIDATION_TRADES = 4
MIN_MODEL_EDGE = 0.00100
EXPLORATION_EDGE = 0.00200
MAX_EXPLORATION_SPREAD = 0.018


def clean_candles(candles, now_ms):
    """Reject malformed/duplicate data and exclude the still-forming candle."""
    result = []
    for candle in candles:
        values = (
            candle.open,
            candle.high,
            candle.low,
            candle.close,
            candle.volume,
        )
        if not all(isfinite(value) for value in values):
            raise ValueError("Non-finite market data")
        if candle.low <= 0 or candle.volume < 0 or not (
            candle.low
            <= min(candle.open, candle.close)
            <= max(candle.open, candle.close)
            <= candle.high
        ):
            raise ValueError("Invalid OHLC data")
        if result and candle.timestamp <= result[-1].timestamp:
            raise ValueError("Unordered or duplicate timestamps")
        if candle.timestamp + MINUTE <= now_ms:
            result.append(candle)
    return result


def features(candles, i):
    window = candles[i - 20 : i + 1]
    closes = [candle.close for candle in window]
    returns = [b / a - 1 for a, b in zip(closes, closes[1:])]
    volatility = max(pstdev(returns), 0.0001)
    return (
        returns[-1] / volatility,
        (closes[-1] / closes[-6] - 1) / (volatility * sqrt(5)),
        (closes[-1] / closes[0] - 1) / (volatility * sqrt(20)),
        (closes[-1] / mean(closes) - 1) / (volatility * sqrt(20)),
    )


def signal_side(strategy, candles, i):
    """Return LONG/SHORT when the strategy has a live directional signal."""
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

    previous_high = max(candle.high for candle in candles[i - 20 : i])
    previous_low = min(candle.low for candle in candles[i - 20 : i])
    if candles[i].close > previous_high:
        return "LONG"
    if candles[i].close < previous_low:
        return "SHORT"
    return None


def exit_price(candle, entry, side, timed_out=False):
    """Deterministic paper exit for both LONG and SHORT."""
    if side == "LONG":
        stop = entry * (1 - STOP)
        take = entry * (1 + TAKE)

        if candle.open <= stop:
            return candle.open, "STOP_GAP"
        if candle.open >= take:
            return take, "TAKE_PROFIT"
        if candle.low <= stop:
            return stop, "STOP_LOSS"
        if candle.high >= take:
            return take, "TAKE_PROFIT"
    else:
        stop = entry * (1 + STOP)
        take = entry * (1 - TAKE)

        if candle.open >= stop:
            return candle.open, "STOP_GAP"
        if candle.open <= take:
            return take, "TAKE_PROFIT"
        if candle.high >= stop:
            return stop, "STOP_LOSS"
        if candle.low <= take:
            return take, "TAKE_PROFIT"

    if timed_out:
        return candle.close, "TIME_EXIT"
    return None


def net_return(entry, exit_value, side="LONG"):
    """Fractional paper return after estimated round-trip fee and slippage."""
    direction = 1.0 if side == "LONG" else -1.0
    gross = direction * (exit_value / entry - 1.0)
    return gross - 2.0 * (FEE + SLIPPAGE)


def outcome(candles, i, side):
    """Signal at close i; execute at the next open with identical exit rules."""
    entry = candles[i + 1].open
    for j in range(i + 1, i + HORIZON + 1):
        value = exit_price(
            candles[j],
            entry,
            side,
            timed_out=j == i + HORIZON,
        )
        if value:
            return net_return(entry, value[0], side)
    raise AssertionError("Missing time exit")


class NearestReturnModel:
    def __init__(self, samples, k=20):
        self.samples = samples
        self.k = k

    def predict(self, x):
        neighbors = sorted(
            self.samples,
            key=lambda row: sum((a - b) ** 2 for a, b in zip(x, row[0])),
        )[: self.k]
        values = [row[1] for row in neighbors]
        return mean(values), pstdev(values)


def rank_asset(symbol, candles):
    """Rank LONG/SHORT candidates using rolling out-of-sample evidence."""
    if len(candles) < 500:
        return []

    if any(
        b.timestamp - a.timestamp != MINUTE
        for a, b in zip(candles[-21:-1], candles[-20:])
    ):
        return []

    boundary = int(len(candles) * 0.70)

    def contiguous(i):
        return all(
            candles[j].timestamp - candles[j - 1].timestamp == MINUTE
            for j in range(i - 19, i + HORIZON + 1)
        )

    train_indices = [
        i
        for i in range(20, boundary - HORIZON)
        if contiguous(i)
    ]
    if len(train_indices) < 200:
        return []

    latest_features = features(candles, len(candles) - 1)
    rows = []

    for side in SIDES:
        model = NearestReturnModel(
            [
                (features(candles, i), outcome(candles, i, side))
                for i in train_indices
            ]
        )
        prediction, spread = model.predict(latest_features)

        for strategy in STRATEGIES:
            validation = []
            next_free = boundary

            for i in range(boundary, len(candles) - HORIZON):
                if i < next_free or not contiguous(i):
                    continue
                if signal_side(strategy, candles, i) != side:
                    continue

                estimate, uncertainty = model.predict(features(candles, i))
                if estimate <= -uncertainty:
                    continue

                validation.append(outcome(candles, i, side))
                next_free = i + HORIZON + 1

            validation_mean = mean(validation) if validation else None
            conservative = prediction - 0.35 * spread
            score = (
                min(conservative, validation_mean)
                if validation_mean is not None
                else conservative
            )
            live_signal = (
                signal_side(strategy, candles, len(candles) - 1) == side
            )

            validated = (
                len(validation) >= MIN_VALIDATION_TRADES
                and validation_mean is not None
                and validation_mean > 0
                and score > MIN_MODEL_EDGE
            )
            exploration = (
                live_signal
                and prediction > EXPLORATION_EDGE
                and score > MIN_MODEL_EDGE
                and spread <= MAX_EXPLORATION_SPREAD
                and (
                    validation_mean is None
                    or validation_mean >= 0.0
                )
            )

            rows.append(
                {
                    "symbol": symbol,
                    "strategy": strategy,
                    "side": side,
                    "eligible": bool(live_signal and (validated or exploration)),
                    "live_signal": bool(live_signal),
                    "validated": bool(validated),
                    "exploratory": bool(exploration and not validated),
                    "score": score,
                    "expected_net_return": prediction,
                    "neighbor_spread": spread,
                    "validation_trades": len(validation),
                    "validation_mean": validation_mean,
                    "train_samples": len(train_indices),
                    "train_label_end": candles[
                        train_indices[-1] + HORIZON
                    ].timestamp,
                    "validation_start": candles[boundary].timestamp,
                }
            )

    return rows


class AIPaperManager:
    """One virtual PLN account with several simultaneous market positions."""

    def __init__(self, path, assets=SUPPORTED_ASSETS, control_path=None):
        self.assets = tuple(assets)
        self.store = LiveStateStore(path)
        self.control_path = Path(
            control_path or Path(path).with_name("ai_control.json")
        )

        loaded = self.store.load()
        if (
            loaded
            and loaded.get("mode") == "PAPER_ONLY"
            and loaded.get("unit") == "PLN"
            and loaded.get("version") in {2, 3}
        ):
            self.state = self._migrate_pln_state(loaded)
        else:
            self.state = self._fresh_state()

        # Rebuild the current UTC day's risk counter from realized trade
        # history. This upgrades legacy "gross losses only" states to the
        # current net daily PnL semantics without manually resetting risk.
        self._reconcile_daily_risk_state()

    def _fresh_state(self):
        return {
            "version": 3,
            "mode": "PAPER_ONLY",
            "model": "cross-market multi-position k-NN v3.2 supervised long-short",
            "unit": "PLN",
            "initial_balance": 0.0,
            "funded_capital": 0.0,
            "balance": 0.0,
            "equity": 0.0,
            "peak": 0.0,
            "daily_loss": 0.0,
            "daily_realized_pnl": 0.0,
            "day": None,
            "realized_pnl": 0.0,
            "unrealized_pnl": 0.0,
            "positions": {},
            "pending": [],
            "decisions": [],
            "trades": [],
            "last_cycle": 0,
            "applied_control_ids": [],
            "funding_received": 0.0,
            "profit_swept": 0.0,
            "profit_transfers": [],
            "accounting_gap": 0.0,
            "accounting_error": False,
            "market_marks": {},
            "strategy_supervisor": {},
            "strategy_learning": {
                strategy: {
                    "trades": 0,
                    "wins": 0,
                    "total_return": 0.0,
                }
                for strategy in STRATEGIES
            },
        }

    def _migrate_pln_state(self, loaded):
        if loaded.get("version") == 3:
            state = loaded
        else:
            state = self._fresh_state()
            for key in (
                "initial_balance",
                "funded_capital",
                "balance",
                "equity",
                "peak",
                "daily_loss",
                "day",
                "realized_pnl",
                "unrealized_pnl",
                "decisions",
                "trades",
                "last_cycle",
                "applied_control_ids",
                "funding_received",
                "strategy_learning",
            ):
                if key in loaded:
                    state[key] = deepcopy(loaded[key])

            old_position = loaded.get("position")
            if old_position and old_position.get("symbol"):
                migrated_position = deepcopy(old_position)
                allocation = float(
                    migrated_position.get("allocation_pln") or 0.0
                )

                # v2 kept the full account balance untouched while a position
                # was open and treated allocation_pln as notional exposure.
                # v3 reserves position principal from free balance and adds it
                # back when calculating equity. Subtract the allocation once
                # during migration or the principal is double-counted.
                state["balance"] = (
                    float(state.get("balance") or 0.0) - allocation
                )
                migrated_position.setdefault(
                    "unrealized_pnl",
                    float(loaded.get("unrealized_pnl") or 0.0),
                )
                state["positions"] = {
                    migrated_position["symbol"]: migrated_position
                }
            old_pending = loaded.get("pending")
            if old_pending:
                state["pending"] = [deepcopy(old_pending)]

        state["version"] = 3
        state["model"] = "cross-market multi-position k-NN v3.2 supervised long-short"
        state.setdefault("positions", {})
        state.setdefault("pending", [])
        state.setdefault("market_marks", {})
        state.setdefault("applied_control_ids", [])
        state.setdefault("funding_received", state.get("initial_balance", 0.0))
        state.setdefault("funded_capital", state.get("initial_balance", 0.0))
        state.setdefault("profit_swept", 0.0)
        state.setdefault("profit_transfers", [])
        state.setdefault("accounting_gap", 0.0)
        state.setdefault("accounting_error", False)
        state.setdefault("strategy_supervisor", {})
        state.setdefault("strategy_learning", {})
        for strategy in STRATEGIES:
            state["strategy_learning"].setdefault(
                strategy,
                {"trades": 0, "wins": 0, "total_return": 0.0},
            )
        return state

    def _record(self, now_ms, action, reason, **extra):
        decision = {
            "timestamp": now_ms,
            "action": action,
            "reason": reason,
            **extra,
        }
        self.state["decision"] = decision
        self.state["decisions"] = (
            self.state["decisions"] + [decision]
        )[-500:]

    def _load_control(self):
        try:
            with self.control_path.open(encoding="utf-8-sig") as handle:
                value = json.load(handle)
            return value if isinstance(value, dict) else {}
        except (OSError, ValueError, TypeError):
            return {}

    def _apply_control(self):
        control = self._load_control()
        events = control.get("funding_events") or []
        applied = set(self.state.get("applied_control_ids") or [])

        for event in events:
            event_id = str(event.get("id") or "")
            if not event_id or event_id in applied:
                continue

            amount = float(event.get("amount") or 0.0)
            applied.add(event_id)
            if amount <= 0:
                continue

            self.state["balance"] += amount
            self.state["initial_balance"] += amount
            self.state["funded_capital"] += amount
            self.state["funding_received"] += amount
            self.state["equity"] += amount
            self.state["peak"] = max(
                self.state["peak"] + amount,
                self.state["equity"],
            )

        self.state["applied_control_ids"] = list(applied)[-500:]

    def _daily_loss_limit(self):
        funded = max(float(self.state.get("funded_capital") or 0.0), 0.0)
        return max(1.0, funded * MAX_DAILY_LOSS_PCT)

    def _apply_daily_realized_result(self, profit):
        """Track current UTC-day realized PnL net of wins and losses."""
        s = self.state
        s["daily_realized_pnl"] = (
            float(s.get("daily_realized_pnl") or 0.0) + float(profit)
        )
        # Risk consumption is the negative part of net daily PnL only.
        # Winning trades therefore offset losing trades from the same UTC day.
        s["daily_loss"] = max(0.0, -s["daily_realized_pnl"])

    def _reconcile_daily_risk_state(self):
        """Upgrade persisted daily risk state to net realized PnL semantics."""
        s = self.state
        day = s.get("day")

        if not day:
            net = float(s.get("daily_realized_pnl") or 0.0)
            s["daily_realized_pnl"] = net
            s["daily_loss"] = max(0.0, -net)
            return

        found = False
        net = 0.0

        for trade in s.get("trades") or []:
            if not isinstance(trade, dict):
                continue

            timestamp = trade.get("exit_timestamp")
            profit = trade.get("profit")
            if timestamp is None or not isinstance(profit, (int, float)):
                continue

            try:
                trade_day = datetime.fromtimestamp(
                    int(timestamp) / 1000,
                    timezone.utc,
                ).date().isoformat()
            except (TypeError, ValueError, OSError, OverflowError):
                continue

            if trade_day != day:
                continue

            found = True
            net += float(profit)

        if not found:
            # Backward-compatible fallback for old persisted states that do not
            # contain enough timestamped trade history to rebuild the day.
            if "daily_realized_pnl" in s:
                net = float(s.get("daily_realized_pnl") or 0.0)
            else:
                net = -float(s.get("daily_loss") or 0.0)

        s["daily_realized_pnl"] = net
        s["daily_loss"] = max(0.0, -net)

    def _allocated_principal(self):
        return sum(
            float(position.get("allocation_pln") or 0.0)
            for position in self.state["positions"].values()
        )

    def _exploratory_slots_used(self):
        open_count = sum(
            1
            for position in self.state["positions"].values()
            if position.get("exploratory")
        )
        pending_count = sum(
            1
            for pending in self.state.get("pending") or []
            if pending.get("exploratory")
        )
        return open_count + pending_count

    def _apply_live_learning(self, row):
        """Apply realized live strategy evidence before final eligibility."""
        learning = self.state["strategy_learning"].get(row["strategy"], {})
        sample_count = int(learning.get("trades", 0))
        observed = (
            float(learning.get("total_return", 0.0)) / sample_count
            if sample_count
            else 0.0
        )
        bonus = LEARNING_WEIGHT * observed if sample_count >= 3 else 0.0

        row["learning_trades"] = sample_count
        row["learning_mean_return"] = observed if sample_count else None
        row["learning_bonus"] = bonus
        row["score"] += bonus

        if row.get("eligible") and row["score"] <= MIN_MODEL_EDGE:
            row["eligible"] = False
            row["eligibility_reason"] = "LIVE_LEARNING_EDGE_REJECTED"

        return row

    def _blocked(self):
        s = self.state

        gap = self._accounting_gap()
        s["accounting_gap"] = gap
        s["accounting_error"] = abs(gap) > 0.01

        if s["peak"] > 0 and s["equity"] <= s["peak"] * (1 - MAX_DRAWDOWN):
            s["halted"] = True
        return bool(
            s.get("halted", False)
            or s.get("accounting_error", False)
            or s["daily_loss"] >= self._daily_loss_limit()
        )

    def _accounting_gap(self):
        s = self.state
        expected = (
            float(s.get("funded_capital") or 0.0)
            + float(s.get("realized_pnl") or 0.0)
            + float(s.get("unrealized_pnl") or 0.0)
            - float(s.get("profit_swept") or 0.0)
        )
        return float(s.get("equity") or 0.0) - expected

    def _mark_equity(self):
        s = self.state
        unrealized = sum(
            float(position.get("unrealized_pnl") or 0.0)
            for position in s["positions"].values()
        )
        principal = self._allocated_principal()
        s["unrealized_pnl"] = unrealized
        s["equity"] = s["balance"] + principal + unrealized
        s["peak"] = max(s["peak"], s["equity"])

        gap = self._accounting_gap()
        s["accounting_gap"] = gap
        s["accounting_error"] = abs(gap) > 0.01

    def _sweep_realized_profit(self, now_ms):
        """Move realized account value above funded capital into an outbox.

        Unrealized gains are never swept. The paper account therefore does not
        compound above the amount explicitly transferred in by the user.
        """
        s = self.state
        target = max(float(s.get("funded_capital") or 0.0), 0.0)
        principal = self._allocated_principal()
        realized_account_value = float(s["balance"]) + principal
        equity_surplus = max(0.0, float(s["equity"]) - target)
        realized_surplus = max(0.0, realized_account_value - target)

        amount = min(
            float(s["balance"]),
            equity_surplus,
            realized_surplus,
        )
        if amount <= 0.000001:
            return None

        event = {
            "id": str(uuid4()),
            "amount": amount,
            "currency": "PLN",
            "created_at_unix": now_ms / 1000.0,
            "paper_only": True,
            "type": "AI_REALIZED_PROFIT_SWEEP",
        }

        s["balance"] -= amount
        s["profit_swept"] = float(s.get("profit_swept") or 0.0) + amount
        s["profit_transfers"] = (
            list(s.get("profit_transfers") or []) + [event]
        )[-1000:]
        self._mark_equity()

        # A payout is not a trading drawdown. Shift the reference peak by the
        # paid-out amount so risk controls compare like with like.
        s["peak"] = max(
            s["equity"],
            max(0.0, float(s.get("peak") or 0.0) - amount),
        )
        return event

    def _manage_positions(self, markets):
        s = self.state
        closed = []

        for symbol, position in list(s["positions"].items()):
            bars = markets.get(symbol, [])
            for candle in bars:
                if candle.timestamp <= position["last_timestamp"]:
                    continue

                position["last_timestamp"] = candle.timestamp
                result = exit_price(
                    candle,
                    position["entry"],
                    position["side"],
                    candle.timestamp >= position["exit_at"],
                )
                mark = result[0] if result else candle.close
                position["mark_price"] = mark
                position["unrealized_pnl"] = position[
                    "allocation_pln"
                ] * net_return(
                    position["entry"],
                    mark,
                    position["side"],
                )

                if result is None and self._blocked():
                    result = (candle.close, "RISK_LIMIT")

                if result:
                    trade_return = net_return(
                        position["entry"],
                        result[0],
                        position["side"],
                    )
                    profit = position["allocation_pln"] * trade_return
                    s["balance"] += position["allocation_pln"] + profit
                    s["realized_pnl"] += profit
                    self._apply_daily_realized_result(profit)

                    learning = s["strategy_learning"].setdefault(
                        position["strategy"],
                        {"trades": 0, "wins": 0, "total_return": 0.0},
                    )
                    learning["trades"] += 1
                    learning["wins"] += int(profit > 0)
                    learning["total_return"] += trade_return

                    s["trades"] = (
                        s["trades"]
                        + [
                            {
                                **position,
                                "exit_price": result[0],
                                "exit_timestamp": candle.timestamp,
                                "profit": profit,
                                "return_fraction": trade_return,
                                "reason": result[1],
                            }
                        ]
                    )[-1000:]
                    closed.append(symbol)
                    break

        for symbol in closed:
            s["positions"].pop(symbol, None)

        self._mark_equity()

    def _execute_pending(self, raw_markets, fresh, ranked_rows, now_ms):
        """Confirm a pending signal on a newer closed candle before entry.

        A pending candidate is never executed only because it was eligible in
        the previous cycle. At least one newer closed candle must exist and the
        exact symbol/strategy/side must still be eligible. If confirmation
        fails, the pending order is cancelled.

        Entry uses the latest observed market price from the raw feed rather
        than retrospectively filling the historical next-candle open.
        """
        s = self.state
        remaining = []
        opened = []
        cancelled = []

        eligible = {
            (row.get("symbol"), row.get("strategy"), row.get("side")): row
            for row in ranked_rows
            if row.get("eligible")
        }

        for pending in list(s.get("pending") or []):
            if len(s["positions"]) >= MAX_OPEN_POSITIONS:
                remaining.append(pending)
                continue

            symbol = pending["symbol"]
            if symbol in s["positions"]:
                cancelled.append(
                    {
                        **pending,
                        "cancel_reason": "POSITION_ALREADY_OPEN",
                    }
                )
                continue

            if self._blocked():
                cancelled.append(
                    {
                        **pending,
                        "cancel_reason": "RISK_BLOCK",
                    }
                )
                continue

            bars = fresh.get(symbol, [])
            if not bars:
                remaining.append(pending)
                continue

            signal_timestamp = int(
                pending.get("signal_timestamp")
                or pending.get("timestamp")
                or 0
            )

            # Wait until at least one completely closed candle newer than the
            # candle that generated the original signal is available.
            if bars[-1].timestamp <= signal_timestamp:
                remaining.append(pending)
                continue

            key = (
                symbol,
                pending.get("strategy"),
                pending.get("side"),
            )
            confirmed = eligible.get(key)
            if confirmed is None:
                cancelled.append(
                    {
                        **pending,
                        "cancel_reason": "SIGNAL_NOT_CONFIRMED",
                        "checked_timestamp": bars[-1].timestamp,
                    }
                )
                continue

            raw_bars = raw_markets.get(symbol, [])
            current_bar = next(
                (
                    candle
                    for candle in reversed(raw_bars)
                    if candle.timestamp <= now_ms
                    and isfinite(candle.close)
                    and candle.close > 0
                ),
                None,
            )
            if current_bar is None:
                remaining.append(pending)
                continue

            equity_base = max(
                0.0,
                min(
                    float(s.get("funded_capital") or 0.0),
                    float(s.get("equity") or 0.0),
                ),
            )
            supervisor_exposure = confirmed.get("supervisor_exposure")
            exposure = (
                float(supervisor_exposure)
                if supervisor_exposure is not None
                else EXPLORATION_POSITION_EXPOSURE
                if confirmed.get("exploratory")
                else PER_POSITION_EXPOSURE
            )
            target = equity_base * exposure
            total_cap = equity_base * MAX_TOTAL_EXPOSURE
            remaining_cap = max(
                0.0,
                total_cap - self._allocated_principal(),
            )
            allocation = min(target, remaining_cap, s["balance"])
            if allocation <= 0:
                cancelled.append(
                    {
                        **pending,
                        "cancel_reason": "NO_AVAILABLE_CAPITAL",
                    }
                )
                continue

            side = pending["side"]
            entry = float(current_bar.close)
            s["balance"] -= allocation
            s["positions"][symbol] = {
                "symbol": symbol,
                "strategy": pending["strategy"],
                "side": side,
                "entry": entry,
                "allocation_pln": allocation,
                "entry_timestamp": now_ms,
                "last_timestamp": bars[-1].timestamp,
                "exit_at": now_ms + HORIZON * MINUTE,
                "stop_loss": (
                    entry * (1 - STOP)
                    if side == "LONG"
                    else entry * (1 + STOP)
                ),
                "take_profit": (
                    entry * (1 + TAKE)
                    if side == "LONG"
                    else entry * (1 - TAKE)
                ),
                "mark_price": entry,
                "unrealized_pnl": -allocation * 2.0 * (FEE + SLIPPAGE),
                "score": confirmed.get("score"),
                "selected_score": pending.get("score"),
                "confirmed_timestamp": bars[-1].timestamp,
                "exploratory": confirmed.get("exploratory", False),
                "supervisor_status": confirmed.get("supervisor_status"),
                "supervisor_probation": confirmed.get(
                    "supervisor_probation",
                    False,
                ),
            }
            opened.append(symbol)

        s["pending"] = remaining
        s["pending_cancelled"] = (
            list(s.get("pending_cancelled") or []) + cancelled
        )[-500:]
        self._mark_equity()
        return {
            "opened": opened,
            "cancelled": cancelled,
        }

    def _select_new_pending(self, rows, fresh, now_ms):
        s = self.state
        occupied = set(s["positions"])
        occupied.update(
            pending["symbol"]
            for pending in s.get("pending") or []
            if pending.get("symbol")
        )

        slots = MAX_OPEN_POSITIONS - len(s["positions"]) - len(s["pending"])
        if slots <= 0 or self._blocked():
            return []

        eligible = [row for row in rows if row.get("eligible")]
        selected = []

        exploratory_slots_used = self._exploratory_slots_used()

        for row in eligible:
            symbol = row["symbol"]
            if symbol in occupied:
                continue
            if (
                row.get("exploratory")
                and exploratory_slots_used >= MAX_EXPLORATORY_POSITIONS
            ):
                continue
            latest_bar = fresh.get(symbol, [None])[-1]
            if latest_bar is None:
                continue

            selected.append(
                {
                    "symbol": symbol,
                    "strategy": row["strategy"],
                    "side": row["side"],
                    "timestamp": latest_bar.timestamp,
                    "signal_timestamp": latest_bar.timestamp,
                    "selected_at": now_ms,
                    "score": row["score"],
                    "exploratory": row.get("exploratory", False),
                    "supervisor_status": row.get("supervisor_status"),
                    "supervisor_probation": row.get(
                        "supervisor_probation",
                        False,
                    ),
                    "supervisor_exposure": row.get("supervisor_exposure"),
                }
            )
            if row.get("exploratory"):
                exploratory_slots_used += 1
            occupied.add(symbol)
            if len(selected) >= slots:
                break

        s["pending"].extend(selected)
        return selected

    def step(self, raw_markets, now_ms, errors=None):
        previous = deepcopy(self.state)
        try:
            state = self._step(raw_markets, now_ms, errors)
            self.store.save(state)
            return state
        except Exception:
            self.state = previous
            raise

    def _step(self, raw_markets, now_ms, errors=None):
        s = self.state
        self._apply_control()

        if now_ms <= s["last_cycle"]:
            self.store.save(s)
            return s

        day = datetime.fromtimestamp(
            now_ms / 1000,
            timezone.utc,
        ).date().isoformat()
        if day != s["day"]:
            s.update(
                day=day,
                daily_loss=0.0,
                daily_realized_pnl=0.0,
                halted=False,
            )

        markets = {}
        issues = dict(errors or {})

        for symbol, raw in raw_markets.items():
            try:
                markets[symbol] = clean_candles(raw, now_ms)
            except (ValueError, TypeError) as exc:
                issues[symbol] = str(exc)

        fresh = {
            symbol: bars
            for symbol, bars in markets.items()
            if len(bars) >= 2
            and 0 <= now_ms - bars[-1].timestamp - MINUTE <= 2 * MINUTE
            and bars[-1].timestamp - bars[-2].timestamp == MINUTE
        }

        for symbol in markets.keys() - fresh.keys():
            issues[symbol] = "Rynek zamknięty, stare dane lub luka w świecach"

        s["market_marks"] = {
            symbol: {
                "price": float(bars[-1].close),
                "timestamp": int(bars[-1].timestamp),
            }
            for symbol, bars in fresh.items()
        }

        if s["balance"] <= 0 and not s["positions"]:
            s.update(
                ranking=[],
                data_issues=issues,
                last_cycle=now_ms,
                pending=[],
                equity=0.0,
                unrealized_pnl=0.0,
                limits={
                    "per_position_exposure": PER_POSITION_EXPOSURE,
                    "max_total_exposure": MAX_TOTAL_EXPOSURE,
                    "max_open_positions": MAX_OPEN_POSITIONS,
                    "daily_loss_pct": MAX_DAILY_LOSS_PCT,
                    "drawdown": MAX_DRAWDOWN,
                    "stop": STOP,
                    "take": TAKE,
                    "horizon_minutes": HORIZON,
                },
            )
            self._record(
                now_ms,
                "WAIT_FUNDS",
                "Brak wirtualnego kapitału. Zasil konto AI z portfela PLN.",
            )
            return s

        rows = []
        for symbol, bars in fresh.items():
            ranked = rank_asset(symbol, bars)
            rows.extend(ranked)
            if not ranked:
                issues[symbol] = "Za mało danych do treningu i walidacji"

        for row in rows:
            self._apply_live_learning(row)

        supervisor = build_strategy_supervisor(s["trades"], STRATEGIES)
        for row in rows:
            supervise_candidate(row, supervisor)

        rows.sort(
            key=lambda row: (
                bool(row.get("eligible")),
                float(row.get("score") or -999.0),
                float(row.get("expected_net_return") or -999.0),
            ),
            reverse=True,
        )

        pending_result = self._execute_pending(
            raw_markets,
            fresh,
            rows,
            now_ms,
        )
        self._manage_positions(fresh)
        swept = self._sweep_realized_profit(now_ms)

        selected = self._select_new_pending(rows, fresh, now_ms)
        self._mark_equity()

        s.update(
            ranking=rows,
            data_issues=issues,
            last_cycle=now_ms,
            last_pending_opened=pending_result["opened"],
            last_pending_cancelled=pending_result["cancelled"],
            strategy_supervisor=supervisor,
            limits={
                "per_position_exposure": PER_POSITION_EXPOSURE,
                "exploration_position_exposure": EXPLORATION_POSITION_EXPOSURE,
                "max_exploratory_positions": MAX_EXPLORATORY_POSITIONS,
                "max_total_exposure": MAX_TOTAL_EXPOSURE,
                "max_open_positions": MAX_OPEN_POSITIONS,
                "daily_loss_pct": MAX_DAILY_LOSS_PCT,
                "daily_loss_limit_pln": self._daily_loss_limit(),
                "drawdown": MAX_DRAWDOWN,
                "stop": STOP,
                "take": TAKE,
                "horizon_minutes": HORIZON,
                "capital_target_pln": float(s.get("funded_capital") or 0.0),
                "profit_swept_pln": float(s.get("profit_swept") or 0.0),
            },
        )

        if swept is not None:
            self._record(
                now_ms,
                "PROFIT_SWEEP",
                "Zrealizowana nadwyżka ponad wpłacony kapitał została przekazana do portfela użytkownika",
                amount_pln=swept["amount"],
                transfer_id=swept["id"],
                open_positions=len(s["positions"]),
            )
        elif self._blocked():
            s["pending"] = []
            self._record(
                now_ms,
                "HALT",
                "Limit dziennej straty lub obsunięcia kapitału",
                open_positions=len(s["positions"]),
            )
        elif selected:
            self._record(
                now_ms,
                "SELECT_MULTI",
                "Wybrano nowe sygnały na różnych aktywach",
                symbols=[row["symbol"] for row in selected],
                sides=[row["side"] for row in selected],
                open_positions=len(s["positions"]),
                pending_count=len(s["pending"]),
                confirmed_opened=pending_result["opened"],
                cancelled_pending=[
                    row.get("symbol")
                    for row in pending_result["cancelled"]
                ],
            )
        elif s["positions"]:
            self._record(
                now_ms,
                "HOLD_MULTI",
                "Zarządzanie otwartymi pozycjami na wielu rynkach",
                symbols=list(s["positions"]),
                open_positions=len(s["positions"]),
                pending_count=len(s["pending"]),
                confirmed_opened=pending_result["opened"],
                cancelled_pending=[
                    row.get("symbol")
                    for row in pending_result["cancelled"]
                ],
            )
        elif s["pending"]:
            self._record(
                now_ms,
                "WAIT_MULTI",
                "Oczekiwanie na kolejne zamknięte świece dla wybranych rynków",
                symbols=[row["symbol"] for row in s["pending"]],
                pending_count=len(s["pending"]),
            )
        else:
            self._record(
                now_ms,
                "CASH",
                "Brak aktywnych sygnałów spełniających warunki paper po kosztach",
            )

        return s

    def run_once(self):
        def fetch(asset):
            try:
                return (
                    asset.symbol,
                    DataProvider().get_candles(
                        asset.symbol,
                        "1m",
                        600,
                    ),
                    None,
                )
            except Exception as exc:
                return asset.symbol, [], str(exc)

        workers = min(8, max(1, len(self.assets)))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(fetch, self.assets))

        return self.step(
            {
                symbol: bars
                for symbol, bars, error in results
                if not error
            },
            int(time() * 1000),
            {
                symbol: error
                for symbol, _, error in results
                if error
            },
        )