"""Autonomous cross-market paper-trading account.

Real market data, virtual PLN only. The module never sends real orders and has
no broker/exchange execution credentials.

The account is deliberately separated from the user's virtual PLN wallet:
funding arrives through ai_control.json events created by the API after the
user confirms a transfer.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timezone
from math import isfinite, sqrt
from pathlib import Path
from statistics import mean, pstdev
from time import time
import json

from src.agent.live_state_store import LiveStateStore
from src.data.assets import SUPPORTED_ASSETS
from src.data.data_provider import DataProvider

MINUTE = 60_000
HORIZON = 15
FEE = 0.0004
SLIPPAGE = 0.0005
EXPOSURE = 0.25
STOP = 0.012
TAKE = 0.024
STRATEGIES = ("trend", "mean_reversion", "breakout")
SIDES = ("LONG", "SHORT")
LEARNING_WEIGHT = 0.20
MAX_DRAWDOWN = 0.08
MAX_DAILY_LOSS_PCT = 0.03
MIN_VALIDATION_TRADES = 2
MIN_MODEL_EDGE = 0.00035
EXPLORATION_EDGE = 0.00150


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
    """Paper exit using deterministic stop/take/time rules."""
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
    """Fractional paper return after round-trip fee and slippage estimates."""
    direction = 1.0 if side == "LONG" else -1.0
    gross = direction * (exit_value / entry - 1.0)
    round_trip_cost = 2.0 * (FEE + SLIPPAGE)
    return gross - round_trip_cost


def outcome(candles, i, side):
    """Signal at close i; execute next open under the same risk/cost rules."""
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
    """Rank LONG/SHORT strategy candidates from rolling out-of-sample evidence."""
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
                # Validation remains conservative, but no longer requires a
                # perfect lower confidence bound on every historical entry.
                if estimate <= -uncertainty:
                    continue

                validation.append(outcome(candles, i, side))
                next_free = i + HORIZON + 1

            validation_mean = mean(validation) if validation else None
            conservative = prediction - 0.50 * spread
            score = min(
                conservative,
                validation_mean if validation_mean is not None else conservative,
            )

            live_signal = signal_side(
                strategy,
                candles,
                len(candles) - 1,
            ) == side

            validated = (
                len(validation) >= MIN_VALIDATION_TRADES
                and validation_mean is not None
                and validation_mean > 0
                and score > MIN_MODEL_EDGE
            )
            exploration = (
                live_signal
                and prediction > EXPLORATION_EDGE
                and validation_mean is not None
                and validation_mean > -0.001
                and len(validation) >= 1
            )

            rows.append(
                dict(
                    symbol=symbol,
                    strategy=strategy,
                    side=side,
                    eligible=bool(live_signal and (validated or exploration)),
                    live_signal=bool(live_signal),
                    validated=bool(validated),
                    exploratory=bool(exploration and not validated),
                    score=score,
                    expected_net_return=prediction,
                    neighbor_spread=spread,
                    validation_trades=len(validation),
                    validation_mean=validation_mean,
                    train_samples=len(train_indices),
                    train_label_end=candles[
                        train_indices[-1] + HORIZON
                    ].timestamp,
                    validation_start=candles[boundary].timestamp,
                )
            )

    return rows


class AIPaperManager:
    """One-account autonomous paper broker selecting across all supplied assets."""

    def __init__(self, path, assets=SUPPORTED_ASSETS, control_path=None):
        self.assets = tuple(assets)
        self.store = LiveStateStore(path)
        self.control_path = Path(
            control_path or Path(path).with_name("ai_control.json")
        )

        loaded = self.store.load()
        if (
            not loaded
            or loaded.get("version") != 2
            or loaded.get("mode") != "PAPER_ONLY"
            or loaded.get("unit") != "PLN"
        ):
            self.state = self._fresh_state()
        else:
            self.state = loaded
            self._normalize_state()

    def _fresh_state(self):
        return dict(
            version=2,
            mode="PAPER_ONLY",
            model="cross-market k-NN v2 long-short",
            unit="PLN",
            initial_balance=0.0,
            funded_capital=0.0,
            balance=0.0,
            equity=0.0,
            peak=0.0,
            daily_loss=0.0,
            day=None,
            realized_pnl=0.0,
            unrealized_pnl=0.0,
            position=None,
            pending=None,
            decisions=[],
            trades=[],
            last_cycle=0,
            applied_control_ids=[],
            funding_received=0.0,
            strategy_learning={
                strategy: dict(
                    trades=0,
                    wins=0,
                    total_return=0.0,
                )
                for strategy in STRATEGIES
            },
        )

    def _normalize_state(self):
        s = self.state
        s.setdefault("funded_capital", s.get("initial_balance", 0.0))
        s.setdefault("realized_pnl", s.get("balance", 0.0) - s.get("initial_balance", 0.0))
        s.setdefault("unrealized_pnl", s.get("equity", 0.0) - s.get("balance", 0.0))
        s.setdefault("applied_control_ids", [])
        s.setdefault("funding_received", s.get("initial_balance", 0.0))
        s.setdefault("strategy_learning", {})
        for strategy in STRATEGIES:
            s["strategy_learning"].setdefault(
                strategy,
                dict(trades=0, wins=0, total_return=0.0),
            )

    def _record(self, now_ms, action, reason, **extra):
        decision = dict(
            timestamp=now_ms,
            action=action,
            reason=reason,
            **extra,
        )
        self.state["decision"] = decision
        self.state["decisions"] = (
            self.state["decisions"] + [decision]
        )[-300:]

    def _load_control(self):
        try:
            with self.control_path.open(encoding="utf-8-sig") as handle:
                value = json.load(handle)
            if not isinstance(value, dict):
                return {}
            return value
        except (OSError, ValueError, TypeError):
            return {}

    def _apply_control(self):
        """Apply API-created funding events exactly once."""
        control = self._load_control()
        events = control.get("funding_events") or []
        applied = set(self.state.get("applied_control_ids") or [])

        changed = False
        for event in events:
            event_id = str(event.get("id") or "")
            if not event_id or event_id in applied:
                continue

            amount = float(event.get("amount") or 0.0)
            if amount <= 0:
                applied.add(event_id)
                changed = True
                continue

            self.state["balance"] += amount
            self.state["equity"] += amount
            self.state["initial_balance"] += amount
            self.state["funded_capital"] += amount
            self.state["funding_received"] += amount
            self.state["peak"] = max(
                self.state["peak"] + amount,
                self.state["equity"],
            )
            applied.add(event_id)
            changed = True

        if changed:
            self.state["applied_control_ids"] = list(applied)[-500:]

    def _daily_loss_limit(self):
        funded = max(float(self.state.get("funded_capital") or 0.0), 0.0)
        return max(1.0, funded * MAX_DAILY_LOSS_PCT)

    def _blocked(self):
        s = self.state
        if s["peak"] > 0 and s["equity"] <= s["peak"] * (1 - MAX_DRAWDOWN):
            s["halted"] = True
        return bool(
            s.get("halted", False)
            or s["daily_loss"] >= self._daily_loss_limit()
        )

    def _manage_position(self, markets):
        s = self.state
        position = s["position"]
        bars = markets.get(position["symbol"], [])

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

            open_pnl = position["allocation_pln"] * net_return(
                position["entry"],
                mark,
                position["side"],
            )
            s["equity"] = s["balance"] + open_pnl
            s["unrealized_pnl"] = open_pnl
            s["peak"] = max(s["peak"], s["equity"])

            if result is None and self._blocked():
                result = (candle.close, "RISK_LIMIT")

            if result:
                trade_return = net_return(
                    position["entry"],
                    result[0],
                    position["side"],
                )
                profit = position["allocation_pln"] * trade_return

                s["balance"] += profit
                s["equity"] = s["balance"]
                s["realized_pnl"] = s["balance"] - s["initial_balance"]
                s["unrealized_pnl"] = 0.0
                s["daily_loss"] += max(0.0, -profit)

                learning = s["strategy_learning"].setdefault(
                    position["strategy"],
                    dict(trades=0, wins=0, total_return=0.0),
                )
                learning["trades"] += 1
                learning["wins"] += int(profit > 0)
                learning["total_return"] += trade_return

                s["trades"] = (
                    s["trades"]
                    + [
                        dict(
                            **position,
                            exit_price=result[0],
                            exit_timestamp=candle.timestamp,
                            profit=profit,
                            return_fraction=trade_return,
                            reason=result[1],
                        )
                    ]
                )[-500:]
                s["position"] = None
                break

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
            s.update(day=day, daily_loss=0.0, halted=False)

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

        # A confirmed transfer is required before any paper trade can start.
        if s["balance"] <= 0 and s["position"] is None:
            s.update(
                ranking=[],
                data_issues=issues,
                last_cycle=now_ms,
                limits=dict(
                    exposure=EXPOSURE,
                    daily_loss_pct=MAX_DAILY_LOSS_PCT,
                    drawdown=MAX_DRAWDOWN,
                    stop=STOP,
                    take=TAKE,
                    horizon_minutes=HORIZON,
                ),
            )
            s["pending"] = None
            s["equity"] = s["balance"]
            s["unrealized_pnl"] = 0.0
            self._record(
                now_ms,
                "WAIT_FUNDS",
                "Brak wirtualnego kapitału. Zasil konto AI z portfela PLN.",
            )
            return s

        pending = s.pop("pending", None)
        s["pending"] = None

        if pending and not s["position"] and not self._blocked():
            bars = fresh.get(pending["symbol"], [])
            entry_at = pending["entry_at"]
            entry_bar = next(
                (
                    candle
                    for candle in bars
                    if candle.timestamp == entry_at
                ),
                None,
            )

            if entry_bar:
                allocation = min(
                    max(0.0, s["balance"] * EXPOSURE),
                    s["balance"],
                )
                side = pending["side"]
                entry = entry_bar.open
                s["position"] = dict(
                    symbol=pending["symbol"],
                    strategy=pending["strategy"],
                    side=side,
                    entry=entry,
                    allocation_pln=allocation,
                    entry_timestamp=entry_bar.timestamp,
                    last_timestamp=entry_bar.timestamp - MINUTE,
                    exit_at=entry_bar.timestamp + (HORIZON - 1) * MINUTE,
                    stop_loss=(
                        entry * (1 - STOP)
                        if side == "LONG"
                        else entry * (1 + STOP)
                    ),
                    take_profit=(
                        entry * (1 + TAKE)
                        if side == "LONG"
                        else entry * (1 - TAKE)
                    ),
                )
            elif bars and bars[-1].timestamp < entry_at:
                s["pending"] = pending

        if s["position"]:
            self._manage_position(markets)
        else:
            s["unrealized_pnl"] = 0.0
            s["equity"] = s["balance"]

        rows = []
        for symbol, bars in fresh.items():
            ranked = rank_asset(symbol, bars)
            rows.extend(ranked)
            if not ranked:
                issues[symbol] = "Za mało danych do treningu i walidacji"

        rows.sort(key=lambda row: row["score"], reverse=True)

        for row in rows:
            learning = s["strategy_learning"].get(
                row["strategy"],
                {},
            )
            sample_count = int(learning.get("trades", 0))
            observed = (
                learning.get("total_return", 0.0) / sample_count
                if sample_count
                else 0.0
            )
            row["learning_trades"] = sample_count
            row["learning_mean_return"] = (
                observed if sample_count else None
            )
            row["learning_bonus"] = (
                LEARNING_WEIGHT * observed
                if sample_count >= 3
                else 0.0
            )
            row["score"] += row["learning_bonus"]

        rows.sort(key=lambda row: row["score"], reverse=True)

        s.update(
            ranking=rows,
            data_issues=issues,
            last_cycle=now_ms,
            limits=dict(
                exposure=EXPOSURE,
                daily_loss_pct=MAX_DAILY_LOSS_PCT,
                daily_loss_limit_pln=self._daily_loss_limit(),
                drawdown=MAX_DRAWDOWN,
                stop=STOP,
                take=TAKE,
                horizon_minutes=HORIZON,
            ),
        )

        if self._blocked():
            s["pending"] = None
            self._record(
                now_ms,
                "HALT",
                "Limit dziennej straty lub obsunięcia kapitału",
            )
        elif s["position"]:
            self._record(
                now_ms,
                "HOLD",
                "Zarządzanie otwartą pozycją",
                **{
                    key: s["position"][key]
                    for key in ("symbol", "strategy", "side")
                },
            )
        elif s["pending"]:
            self._record(
                now_ms,
                "WAIT",
                "Oczekiwanie na następną zamkniętą świecę",
                symbol=s["pending"]["symbol"],
                strategy=s["pending"]["strategy"],
                side=s["pending"]["side"],
            )
        else:
            eligible = [
                row
                for row in rows
                if row["eligible"]
            ]

            if eligible:
                best = eligible[0]
                latest_bar = fresh[best["symbol"]][-1]
                s["pending"] = dict(
                    symbol=best["symbol"],
                    strategy=best["strategy"],
                    side=best["side"],
                    timestamp=latest_bar.timestamp,
                    entry_at=((now_ms + MINUTE - 1) // MINUTE) * MINUTE,
                    score=best["score"],
                    exploratory=best.get("exploratory", False),
                )
                self._record(
                    now_ms,
                    "SELECT",
                    (
                        "Wybrano sygnał paper po kosztach i kontroli ryzyka"
                        if not best.get("exploratory")
                        else "Wybrano kontrolowany sygnał eksploracyjny paper"
                    ),
                    symbol=best["symbol"],
                    strategy=best["strategy"],
                    side=best["side"],
                    score=best["score"],
                )
            else:
                self._record(
                    now_ms,
                    "CASH",
                    "Brak aktywnego sygnału spełniającego warunki paper po kosztach",
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

        workers = min(6, max(1, len(self.assets)))
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
