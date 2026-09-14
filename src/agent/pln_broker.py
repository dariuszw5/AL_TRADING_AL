"""Fractional exposure simulator in PLN. Never connects to a broker.

The target is realized capital, including capital reserved in positions, not
1000 PLN of free cash in addition to those positions. Legacy unit accounts
are archived separately, never relabelled as PLN.
"""
from contextlib import contextmanager
from copy import deepcopy
import json
import math
from pathlib import Path
import sqlite3

from src.agent.virtual_broker import FEE, SLIPPAGE, STOP, TAKE


def initial_state(reserve=None):
    if reserve and reserve.get('currency', 'PLN') != 'PLN':
        raise ValueError('Existing reserve requires explicit currency migration')
    wallet = {'balance': 0.0, 'total_deposited': 0.0,
              'total_withdrawn': 0.0, 'profit_transferred': 0.0,
              'topups': 0.0, **(reserve or {})}
    if not math.isfinite(float(wallet['balance'])) or wallet['balance'] < 0:
        raise ValueError('Invalid existing reserve balance')
    return {'version': 2, 'currency': 'PLN', 'initial_balance': 1000.0,
            'balance': 1000.0, 'positions': {}, 'trades': [],
            'equity_curve': [], 'user_portfolio': wallet, 'transfers': [],
            'processed': {}, 'realized_profit': 0.0, 'realized_by_symbol': {}, 'execution_enabled': False}


class PlnLedger:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.path = self.directory / 'pln_ledger.sqlite3'

    @contextmanager
    def transaction(self):
        self.directory.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path, timeout=30) as db:
            db.execute('CREATE TABLE IF NOT EXISTS ledger (id INTEGER PRIMARY KEY, state TEXT NOT NULL)')
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT state FROM ledger WHERE id=1').fetchone()
            if row:
                state = json.loads(row[0])
            else:
                reserve_path = self.directory / 'user_portfolio.json'
                reserve = json.loads(reserve_path.read_text(encoding='utf-8')) if reserve_path.exists() else None
                state = initial_state(reserve)
                old = self.directory / 'ai_research.json'
                if old.exists():
                    state['legacy_archive'] = json.loads(old.read_text(encoding='utf-8')).get('virtual_broker', {})
            yield state
            db.execute('INSERT OR REPLACE INTO ledger VALUES (1, ?)',
                       (json.dumps(state, allow_nan=False),))


class PlnBroker:
    def __init__(self, state):
        self.data = state

    def rebalance(self, timestamp):
        s = self.data
        wallet = s['user_portfolio']
        difference = round(s['balance'] - 1000, 2)
        transfer = difference if difference > 0 else -min(-difference, wallet['balance'])
        transfer = round(transfer, 2)
        if transfer:
            s['balance'] = round(s['balance'] - transfer, 2)
            wallet['balance'] = round(wallet['balance'] + transfer, 2)
            key = 'profit_transferred' if transfer > 0 else 'topups'
            wallet[key] = round(wallet.get(key, 0) + abs(transfer), 2)
            s['transfers'].append({'id': len(s['transfers']) + 1,
                                  'timestamp': timestamp, 'amount': abs(transfer),
                                  'direction': 'TO_RESERVE' if transfer > 0 else 'TO_TRADING'})
        s['shortfall'] = max(0, round(1000 - s['balance'], 2))

    def process(self, symbol, candle, signal, fx, now):
        s = self.data
        if (not math.isfinite(fx) or fx <= 0 or
                now - candle.timestamp > 180000 or candle.timestamp > now or
                candle.timestamp <= s['processed'].get(symbol, -1)):
            return
        if any(not math.isfinite(v) or v <= 0 for v in
               (candle.open, candle.high, candle.low, candle.close)):
            return
        if not candle.low <= min(candle.open, candle.close) <= max(candle.open, candle.close) <= candle.high:
            return
        s['processed'][symbol] = candle.timestamp
        position = s['positions'].get(symbol)
        if position:
            exit_price = None
            if candle.open <= position['stop']:
                exit_price, reason = candle.open, 'STOP_GAP'
            elif candle.low <= position['stop']:
                exit_price, reason = position['stop'], 'STOP_LOSS'
            elif candle.high >= position['take']:
                exit_price, reason = position['take'], 'TAKE_PROFIT'
            if exit_price is not None:
                proceeds = position['quantity'] * exit_price * (1-SLIPPAGE) * (1-FEE) * fx
                profit = round(proceeds - position['cost_pln'], 2)
                s['balance'] = round(s['balance'] + profit, 2)
                s['realized_profit'] = round(s['realized_profit'] + profit, 2)
                totals = s.setdefault('realized_by_symbol', {})
                totals[symbol] = round(totals.get(symbol, 0) + profit, 2)
                s['trades'].append({**position, 'profit': profit, 'currency': 'PLN',
                                    'exit_price': exit_price, 'exit_fx': fx,
                                    'exit_timestamp': candle.timestamp, 'reason': reason})
                del s['positions'][symbol]
                self.rebalance(now)
            return  # Never close and reopen on the same candle.
        self.rebalance(now)
        reserved = sum(p['cost_pln'] for p in s['positions'].values())
        budget = round(min(200.0, s['balance'] - reserved), 2)
        if not signal or s['shortfall'] > 0 or budget < 1:
            return
        entry = candle.close * (1 + SLIPPAGE)
        s['positions'][symbol] = {'symbol': symbol, 'entry': entry,
            'entry_fx': fx, 'cost_pln': budget, 'quantity': budget / (entry * fx * (1+FEE)),
            'opened_at': candle.timestamp, 'stop': entry * (1-STOP),
            'take': entry * (1+TAKE)}

    def snapshot(self, prices, timestamp):
        s = self.data
        equity = s['balance']
        complete = True
        for symbol, p in s['positions'].items():
            quote = prices.get(symbol)
            if quote is None:
                p['unrealized_pln'] = None
                complete = False
                continue
            price, fx = quote
            p['unrealized_pln'] = round(p['quantity'] * price * fx * (1-SLIPPAGE) * (1-FEE) - p['cost_pln'], 2)
            equity += p['unrealized_pln']
        s['free_cash'] = round(s['balance'] - sum(p['cost_pln'] for p in s['positions'].values()), 2)
        s['valuation_complete'] = complete
        s['equity'] = round(equity, 2) if complete else None
        if complete:
            s['equity_curve'].append({'timestamp': timestamp, 'balance': s['balance'],
                                     'equity': s['equity'], 'open_positions': len(s['positions'])})
        s['equity_curve'] = s['equity_curve'][-1000:]

    def public_state(self):
        state = deepcopy(self.data)
        state.pop('legacy_archive', None)
        state['trades'] = state['trades'][-300:]
        state['transfers'] = state['transfers'][-300:]
        return state
