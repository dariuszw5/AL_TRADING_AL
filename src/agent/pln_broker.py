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
from datetime import datetime, timezone

from src.agent.virtual_broker import FEE, SLIPPAGE, STOP, TAKE


TARGET_CAPITAL = 1000.0
# Ten virtual slots let the research portfolio track the Top 10 candidates
# while keeping the same 1000 PLN capital and a limited per-trade loss.
MAX_POSITION_COST = 100.0
MAX_POSITIONS = 10
MAX_CLASS_EXPOSURE = 300.0
DAILY_LOSS_LIMIT = 20.0
MAX_DRAWDOWN = 0.05


def _day(timestamp):
    return datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc).date().isoformat()


def _risk_state():
    return {
        'daily_loss_limit_pln': DAILY_LOSS_LIMIT,
        'max_drawdown_percent': MAX_DRAWDOWN,
        'max_position_cost_pln': MAX_POSITION_COST,
        'max_positions': MAX_POSITIONS,
        'max_class_exposure_pln': MAX_CLASS_EXPOSURE,
        'daily_loss_pln': 0.0,
        'peak_equity_pln': TARGET_CAPITAL,
        'halted': False,
        'halt_reason': None,
        'day': None,
    }


def initial_state(reserve=None):
    if reserve and reserve.get('currency', 'PLN') != 'PLN':
        raise ValueError('Existing reserve requires explicit currency migration')
    wallet = {'balance': 0.0, 'total_deposited': 0.0,
              'total_withdrawn': 0.0, 'profit_transferred': 0.0,
              'topups': 0.0, **(reserve or {})}
    if not math.isfinite(float(wallet['balance'])) or wallet['balance'] < 0:
        raise ValueError('Invalid existing reserve balance')
    return {'version': 3, 'currency': 'PLN', 'initial_balance': TARGET_CAPITAL,
            'balance': TARGET_CAPITAL, 'positions': {}, 'trades': [],
            'equity_curve': [], 'user_portfolio': wallet, 'transfers': [],
            'processed': {}, 'realized_profit': 0.0, 'realized_by_symbol': {},
            'risk': _risk_state(), 'decision_log': [], 'daily_equity': [],
            'execution_enabled': False}


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
        self.data.setdefault('risk', _risk_state())
        self.data.setdefault('decision_log', [])
        self.data.setdefault('daily_equity', [])
        for key, value in _risk_state().items():
            self.data['risk'].setdefault(key, value)

    def _refresh_day(self, timestamp):
        risk = self.data['risk']
        today = _day(timestamp)
        if risk['day'] == today:
            return
        risk['day'] = today
        risk['daily_loss_pln'] = 0.0
        # A daily loss halt clears on the next UTC day; a drawdown halt does not.
        if risk['halt_reason'] == 'DAILY_LOSS_LIMIT':
            risk['halted'] = False
            risk['halt_reason'] = None

    def _apply_equity_risk(self, equity, timestamp):
        self._refresh_day(timestamp)
        risk = self.data['risk']
        risk['peak_equity_pln'] = round(max(risk['peak_equity_pln'], equity), 2)
        if equity <= risk['peak_equity_pln'] * (1 - risk['max_drawdown_percent']):
            risk['halted'] = True
            risk['halt_reason'] = 'MAX_DRAWDOWN'

    def _record_decision(self, *, symbol, asset_type, candle, signal, action,
                         strategy=None, score=None, note=None,
                         confidence_probability=None, validation_trades=None):
        self.data['decision_log'].append({
            'timestamp': candle.timestamp,
            'symbol': symbol,
            'asset_type': asset_type,
            'close': candle.close,
            'signal': bool(signal),
            'action': action,
            'strategy': strategy,
            'score': score,
            'confidence_probability': confidence_probability,
            'validation_trades': validation_trades,
            'note': note,
        })
        self.data['decision_log'] = self.data['decision_log'][-1000:]

    def rebalance(self, timestamp):
        s = self.data
        wallet = s['user_portfolio']
        difference = round(s['balance'] - TARGET_CAPITAL, 2)
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
        s['shortfall'] = max(0, round(TARGET_CAPITAL - s['balance'], 2))

    def close_for_rotation(self, symbol, candle, fx, now, *, note='Poza rankingiem Top 10'):
        """Close a simulated position when its asset leaves the selected universe."""
        position = self.data['positions'].get(symbol)
        if position is None or not math.isfinite(fx) or fx <= 0:
            return 'ROTATION_DEFERRED'
        exit_price = candle.close * (1 - SLIPPAGE)
        proceeds = position['quantity'] * exit_price * (1 - FEE) * fx
        profit = round(proceeds - position['cost_pln'], 2)
        s = self.data
        s['balance'] = round(s['balance'] + profit, 2)
        s['realized_profit'] = round(s['realized_profit'] + profit, 2)
        totals = s.setdefault('realized_by_symbol', {})
        totals[symbol] = round(totals.get(symbol, 0) + profit, 2)
        s['trades'].append({**position, 'profit': profit, 'currency': 'PLN',
                            'exit_price': exit_price, 'exit_fx': fx,
                            'exit_timestamp': candle.timestamp, 'reason': 'ROTATED_OUT'})
        del s['positions'][symbol]
        if profit < 0:
            risk = s['risk']
            risk['daily_loss_pln'] = round(risk['daily_loss_pln'] - profit, 2)
            if risk['daily_loss_pln'] >= risk['daily_loss_limit_pln']:
                risk['halted'] = True
                risk['halt_reason'] = 'DAILY_LOSS_LIMIT'
        self.rebalance(now)
        self._record_decision(symbol=symbol, asset_type=position.get('asset_type', 'other'),
                              candle=candle, signal=False, action='ROTATED_OUT', note=note)
        return 'ROTATED_OUT'

    def process(self, symbol, candle, signal, fx, now, *, asset_type='other',
                strategy=None, score=None, note=None,
                confidence_probability=None, validation_trades=None):
        s = self.data
        # Direct callers that do not provide a category keep independent limits.
        # The production runner always supplies the configured asset type.
        risk_class = symbol if asset_type == 'other' else asset_type
        if (not math.isfinite(fx) or fx <= 0 or
                now - candle.timestamp > 180000 or candle.timestamp > now or
                candle.timestamp <= s['processed'].get(symbol, -1)):
            return 'STALE_OR_DUPLICATE'
        if any(not math.isfinite(v) or v <= 0 for v in
               (candle.open, candle.high, candle.low, candle.close)):
            return 'INVALID_CANDLE'
        if not candle.low <= min(candle.open, candle.close) <= max(candle.open, candle.close) <= candle.high:
            return 'INVALID_CANDLE'
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
                risk = s['risk']
                if profit < 0:
                    risk['daily_loss_pln'] = round(risk['daily_loss_pln'] - profit, 2)
                    if risk['daily_loss_pln'] >= risk['daily_loss_limit_pln']:
                        risk['halted'] = True
                        risk['halt_reason'] = 'DAILY_LOSS_LIMIT'
                self.rebalance(now)
                action = reason
            else:
                action = 'HOLD'
            self._record_decision(symbol=symbol, asset_type=asset_type, candle=candle,
                                  signal=signal, action=action, strategy=strategy, score=score)
            return action  # Never close and reopen on the same candle.
        self.rebalance(now)
        self._refresh_day(now)
        risk = s['risk']
        if risk['halted']:
            action = 'RISK_HALT'
            self._record_decision(symbol=symbol, asset_type=asset_type, candle=candle,
                                  signal=signal, action=action, strategy=strategy, score=score,
                                  note=risk['halt_reason'], confidence_probability=confidence_probability,
                                  validation_trades=validation_trades)
            return action
        reserved = sum(p['cost_pln'] for p in s['positions'].values())
        class_reserved = sum(p['cost_pln'] for p in s['positions'].values()
                             if p.get('risk_class', p.get('asset_type')) == risk_class)
        risk_per_cost = STOP + 2 * (FEE + SLIPPAGE)
        daily_left = max(0.0, risk['daily_loss_limit_pln'] - risk['daily_loss_pln'])
        budget = round(min(risk['max_position_cost_pln'], s['balance'] - reserved,
                           risk['max_class_exposure_pln'] - class_reserved,
                           daily_left / risk_per_cost), 2)
        if not signal:
            action = 'GEO_RISK_FILTER' if note else 'NO_SIGNAL'
        elif s['shortfall'] > 0:
            action = 'CAPITAL_SHORTFALL'
        elif len(s['positions']) >= risk['max_positions']:
            action = 'MAX_POSITIONS'
        elif budget < 1:
            action = 'RISK_BUDGET'
        else:
            action = None
        if action:
            self._record_decision(symbol=symbol, asset_type=asset_type, candle=candle,
                                  signal=signal, action=action, strategy=strategy, score=score,
                                  note=note, confidence_probability=confidence_probability,
                                  validation_trades=validation_trades)
            return action
        entry = candle.close * (1 + SLIPPAGE)
        s['positions'][symbol] = {'symbol': symbol, 'entry': entry,
            'entry_fx': fx, 'cost_pln': budget, 'quantity': budget / (entry * fx * (1+FEE)),
            'opened_at': candle.timestamp, 'stop': entry * (1-STOP),
            'take': entry * (1+TAKE), 'asset_type': asset_type, 'risk_class': risk_class,
            'max_loss_pln': round(budget * risk_per_cost, 2),
            'confidence_probability': confidence_probability,
            'validation_trades': validation_trades}
        self._record_decision(symbol=symbol, asset_type=asset_type, candle=candle,
                              signal=signal, action='OPEN_LONG', strategy=strategy, score=score,
                              confidence_probability=confidence_probability,
                              validation_trades=validation_trades)
        return 'OPEN_LONG'

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
            self._apply_equity_risk(s['equity'], timestamp)
            s['equity_curve'].append({'timestamp': timestamp, 'balance': s['balance'],
                                     'equity': s['equity'], 'open_positions': len(s['positions'])})
            point = {'date': _day(timestamp), 'timestamp': timestamp,
                     'equity': s['equity'], 'balance': s['balance'],
                     'open_positions': len(s['positions'])}
            if s['daily_equity'] and s['daily_equity'][-1]['date'] == point['date']:
                s['daily_equity'][-1] = point
            else:
                s['daily_equity'].append(point)
        s['equity_curve'] = s['equity_curve'][-1000:]
        s['daily_equity'] = s['daily_equity'][-400:]

    def public_state(self):
        from src.agent.probability_calibration import calibration_report
        state = deepcopy(self.data)
        state.pop('legacy_archive', None)
        state['trades'] = state['trades'][-300:]
        state['transfers'] = state['transfers'][-300:]
        state['decision_log'] = state['decision_log'][-300:]
        state['daily_equity'] = state['daily_equity'][-400:]
        state['probability_calibration'] = calibration_report(state['trades'])
        return state
