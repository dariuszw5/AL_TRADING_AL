"""Local k-NN strategy selector and isolated, long-only paper account.

No broker connector, API keys, real orders or language-model execution tools.
Prices are treated as fractional return indices (not futures contracts or PLN).
"""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timezone
from math import isfinite, sqrt
from statistics import mean, pstdev
from time import time

from src.agent.live_state_store import LiveStateStore
from src.data.assets import SUPPORTED_ASSETS
from src.data.data_provider import DataProvider

MINUTE = 60_000
HORIZON = 10
FEE = 0.0004
SLIPPAGE = 0.0005
EXPOSURE = 0.20
STOP = 0.01
TAKE = 0.02
STRATEGIES = ('trend', 'mean_reversion', 'breakout')
LEARNING_WEIGHT = 0.25
USER_PORTFOLIO_PATH = 'data/live_state/user_portfolio.json'


def clean_candles(candles, now_ms):
    """Reject malformed/duplicate data, and exclude the still-forming candle."""
    result = []
    for c in candles:
        values = (c.open, c.high, c.low, c.close, c.volume)
        if not all(isfinite(v) for v in values):
            raise ValueError('Non-finite market data')
        if c.low <= 0 or c.volume < 0 or not (
            c.low <= min(c.open, c.close) <= max(c.open, c.close) <= c.high
        ):
            raise ValueError('Invalid OHLC data')
        if result and c.timestamp <= result[-1].timestamp:
            raise ValueError('Unordered or duplicate timestamps')
        if c.timestamp + MINUTE <= now_ms:
            result.append(c)
    return result


def features(candles, i):
    window = candles[i-20:i+1]
    closes = [c.close for c in window]
    returns = [b / a - 1 for a, b in zip(closes, closes[1:])]
    volatility = max(pstdev(returns), 0.0001)
    return (
        returns[-1] / volatility,
        (closes[-1] / closes[-6] - 1) / (volatility * sqrt(5)),
        (closes[-1] / closes[0] - 1) / (volatility * sqrt(20)),
        (closes[-1] / mean(closes) - 1) / (volatility * sqrt(20)),
    )


def signal(strategy, candles, i):
    f = features(candles, i)
    if strategy == 'trend':
        return f[1] > 0.5 and f[2] > 0.5
    if strategy == 'mean_reversion':
        return f[3] < -0.5 and f[0] > 0
    return candles[i].close > max(c.high for c in candles[i-20:i])


def exit_price(candle, entry, timed_out=False):
    stop, take = entry * (1 - STOP), entry * (1 + TAKE)
    # Gaps can exceed the stop; when both levels are hit, assume stop first.
    if candle.open <= stop:
        return candle.open, 'STOP_GAP'
    if candle.open >= take:
        return take, 'TAKE_PROFIT'
    if candle.low <= stop:
        return stop, 'STOP_LOSS'
    if candle.high >= take:
        return take, 'TAKE_PROFIT'
    if timed_out:
        return candle.close, 'TIME_EXIT'
    return None


def net_return(entry, exit_value):
    bought = entry * (1 + SLIPPAGE)
    sold = exit_value * (1 - SLIPPAGE)
    return (sold * (1 - FEE) - bought * (1 + FEE)) / (bought * (1 + FEE))


def outcome(candles, i):
    """Signal at close i; execute next open, using the same risk/cost rules."""
    entry = candles[i+1].open
    for j in range(i+1, i+HORIZON+1):
        value = exit_price(candles[j], entry, j == i+HORIZON)
        if value:
            return net_return(entry, value[0])
    raise AssertionError('Missing time exit')


class NearestReturnModel:
    def __init__(self, samples, k=20):
        self.samples = samples
        self.k = k

    def predict(self, x):
        neighbors = sorted(
            self.samples, key=lambda row: sum((a-b)**2 for a, b in zip(x, row[0]))
        )[:self.k]
        values = [row[1] for row in neighbors]
        # Conservative ranking heuristic, NOT a calibrated probability/guarantee.
        return mean(values), pstdev(values)


def rank_asset(symbol, candles):
    if len(candles) < 500:
        return []
    if any(b.timestamp - a.timestamp != MINUTE
           for a, b in zip(candles[-21:-1], candles[-20:])):
        return []
    boundary = int(len(candles) * 0.70)
    contiguous = lambda i: all(
        candles[j].timestamp - candles[j-1].timestamp == MINUTE
        for j in range(i-19, i+HORIZON+1)
    )
    # Labels in training finish strictly before the validation boundary.
    train_indices = [i for i in range(20, boundary-HORIZON) if contiguous(i)]
    if len(train_indices) < 200:
        return []
    model = NearestReturnModel([(features(candles, i), outcome(candles, i))
                                for i in train_indices])
    prediction, spread = model.predict(features(candles, len(candles)-1))
    rows = []
    for strategy in STRATEGIES:
        validation = []
        next_free = boundary
        for i in range(boundary, len(candles)-HORIZON):
            if i < next_free or not contiguous(i) or not signal(strategy, candles, i):
                continue
            estimate, uncertainty = model.predict(features(candles, i))
            if estimate - uncertainty <= 0:
                continue
            validation.append(outcome(candles, i))
            next_free = i + HORIZON + 1
        score = min(prediction - spread, mean(validation)) if validation else -1.0
        eligible = (len(validation) >= 5 and score > 0 and
                    signal(strategy, candles, len(candles)-1))
        rows.append(dict(symbol=symbol, strategy=strategy, eligible=eligible,
                         score=score, expected_net_return=prediction,
                         neighbor_spread=spread, validation_trades=len(validation),
                         validation_mean=mean(validation) if validation else None,
                         train_samples=len(train_indices),
                         train_label_end=candles[train_indices[-1]+HORIZON].timestamp,
                         validation_start=candles[boundary].timestamp))
    return rows


class AIPaperManager:
    def __init__(self, path, assets=SUPPORTED_ASSETS):
        self.assets = tuple(assets)
        self.store = LiveStateStore(path)
        self.state = self.store.load() or dict(
            version=1, mode='PAPER_ONLY', model='k-NN returns v1 + online stats',
            unit='simulation_units', initial_balance=1000.0, balance=1000.0,
            equity=1000.0, peak=1000.0, daily_loss=0.0, day=None,
            realized_pnl=0.0, unrealized_pnl=0.0,
            profit_swept=0.0, profit_transfers=[],
            position=None, pending=None, decisions=[], trades=[], last_cycle=0,
            strategy_learning={strategy: dict(trades=0, wins=0, total_return=0.0)
                               for strategy in STRATEGIES},
        )
        if self.state.get('version') != 1 or self.state.get('mode') != 'PAPER_ONLY':
            raise ValueError('Unsupported AI paper state')
        self.state.setdefault('strategy_learning', {})
        self.state.setdefault('realized_pnl', self.state.get('balance', 1000.0)
                             - self.state.get('initial_balance', 1000.0))
        self.state.setdefault('unrealized_pnl', self.state.get('equity', 1000.0)
                             - self.state.get('balance', 1000.0))
        self.state.setdefault('profit_swept', 0.0)
        self.state.setdefault('profit_transfers', [])
        for strategy in STRATEGIES:
            self.state['strategy_learning'].setdefault(
                strategy, dict(trades=0, wins=0, total_return=0.0))

    def _record(self, now_ms, action, reason, **extra):
        decision = dict(timestamp=now_ms, action=action, reason=reason, **extra)
        self.state['decision'] = decision
        self.state['decisions'] = (self.state['decisions'] + [decision])[-300:]

    def _blocked(self):
        s = self.state
        if s['equity'] <= s['peak'] * 0.95:
            s['halted'] = True
        return s.get('halted', False) or s['daily_loss'] >= 20

    def _manage_position(self, markets):
        s = self.state
        p = s['position']
        for c in markets.get(p['symbol'], []):
            if c.timestamp <= p['last_timestamp']:
                continue
            p['last_timestamp'] = c.timestamp
            result = exit_price(c, p['entry'], c.timestamp >= p['exit_at'])
            mark = result[0] if result else c.close
            s['equity'] = s['balance'] + p['allocation'] * net_return(p['entry'], mark)
            s['unrealized_pnl'] = s['equity'] - s['balance']
            s['peak'] = max(s['peak'], s['equity'])
            if result is None and self._blocked():
                result = (c.close, 'RISK_LIMIT')
            if result:
                profit = p['allocation'] * net_return(p['entry'], result[0])
                s['balance'] += profit
                s['equity'] = s['balance']
                s['realized_pnl'] = s['balance'] - s['initial_balance']
                s['unrealized_pnl'] = 0.0
                s['daily_loss'] += max(0, -profit)
                learning = s['strategy_learning'].setdefault(
                    p['strategy'], dict(trades=0, wins=0, total_return=0.0))
                learning['trades'] += 1
                learning['wins'] += int(profit > 0)
                learning['total_return'] += net_return(p['entry'], result[0])
                s['trades'] = (s['trades'] + [dict(
                    **p, exit_price=result[0], exit_timestamp=c.timestamp,
                    profit=profit, reason=result[1])])[-300:]
                s['position'] = None
                break

    def _sweep_surplus(self, now_ms):
        """Legacy compatibility hook.

        AI account values are denominated in simulation_units.

        They must never be copied 1:1 into the user's PLN cash ledger.
        Historical profit_swept/profit_transfers fields are preserved for
        audit and a future explicit migration, but no new portfolio transfer
        is performed here.
        """
        return None

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
        if now_ms <= s['last_cycle']:
            return s
        day = datetime.fromtimestamp(now_ms/1000, timezone.utc).date().isoformat()
        if day != s['day']:
            s.update(day=day, daily_loss=0.0)
        markets, issues = {}, dict(errors or {})
        for symbol, raw in raw_markets.items():
            try:
                markets[symbol] = clean_candles(raw, now_ms)
            except (ValueError, TypeError) as exc:
                issues[symbol] = str(exc)
        fresh = {symbol: bars for symbol, bars in markets.items()
                 if len(bars) >= 2 and 0 <= now_ms-bars[-1].timestamp-MINUTE <= 2*MINUTE
                 and bars[-1].timestamp-bars[-2].timestamp == MINUTE}
        for symbol in markets.keys() - fresh.keys():
            issues[symbol] = 'Rynek zamknięty, stare dane lub luka w świecach'

        pending = s.pop('pending', None)
        s['pending'] = None
        if pending and not s['position'] and not self._blocked():
            bars = fresh.get(pending['symbol'], [])
            entry_at = pending['entry_at']
            entry_bar = next((c for c in bars if c.timestamp == entry_at), None)
            if entry_bar:
                s['position'] = dict(symbol=pending['symbol'], strategy=pending['strategy'],
                    entry=entry_bar.open, allocation=s['balance']*EXPOSURE,
                    entry_timestamp=entry_bar.timestamp,
                    last_timestamp=entry_bar.timestamp-MINUTE,
                    exit_at=entry_bar.timestamp+(HORIZON-1)*MINUTE)
            elif bars and bars[-1].timestamp < entry_at:
                s['pending'] = pending
        if s['position']:
            self._manage_position(markets)
        else:
            s['unrealized_pnl'] = 0.0
        self._sweep_surplus(now_ms)
        rows = []
        for symbol, bars in fresh.items():
            ranked = rank_asset(symbol, bars)
            rows.extend(ranked)
            if not ranked:
                issues[symbol] = 'Za mało danych do treningu i walidacji'
        for row in rows:
            learning = s['strategy_learning'].get(row['strategy'], {})
            sample_count = int(learning.get('trades', 0))
            observed = (learning.get('total_return', 0.0) / sample_count
                        if sample_count else 0.0)
            # Online results are a bounded tie-breaker, never a reason to
            # override a negative market model score.
            row['learning_trades'] = sample_count
            row['learning_mean_return'] = observed if sample_count else None
            row['learning_bonus'] = (LEARNING_WEIGHT * observed
                                      if sample_count >= 3 else 0.0)
            row['score'] += row['learning_bonus']

        # Selection must use the FINAL score after the bounded online bonus.
        rows.sort(key=lambda row: row['score'], reverse=True)

        s.update(ranking=rows, data_issues=issues, last_cycle=now_ms,
                 limits=dict(exposure=EXPOSURE, daily_loss=20, drawdown=0.05,
                             stop=STOP, take=TAKE, horizon_minutes=HORIZON))
        if self._blocked():
            s['pending'] = None
            self._record(now_ms, 'HALT', 'Limit strat lub obsunięcia kapitału')
        elif s['position']:
            self._record(now_ms, 'HOLD', 'Zarządzanie otwartą pozycją', **{
                key: s['position'][key] for key in ('symbol', 'strategy')})
        elif s['pending']:
            self._record(now_ms, 'WAIT', 'Oczekiwanie na następną świecę',
                         symbol=s['pending']['symbol'], strategy=s['pending']['strategy'])
        else:
            eligible = [r for r in rows if r['eligible']]
            if eligible:
                best = eligible[0]
                s['pending'] = dict(symbol=best['symbol'], strategy=best['strategy'],
                                     timestamp=fresh[best['symbol']][-1].timestamp,
                                     entry_at=((now_ms+MINUTE-1)//MINUTE)*MINUTE)
                self._record(now_ms, 'SELECT', 'Dodatnia ocena modelu i walidacji po kosztach',
                             symbol=best['symbol'], strategy=best['strategy'])
            else:
                self._record(now_ms, 'CASH', 'Brak potwierdzonej przewagi po kosztach')
        return s

    def run_once(self):
        def fetch(asset):
            try:
                return asset.symbol, DataProvider().get_candles(asset.symbol, '1m', 600), None
            except Exception as exc:
                return asset.symbol, [], str(exc)
        with ThreadPoolExecutor(max_workers=3) as pool:
            results = list(pool.map(fetch, self.assets))
        return self.step({s: bars for s, bars, error in results if not error},
                         int(time()*1000), {s: error for s, _, error in results if error})
