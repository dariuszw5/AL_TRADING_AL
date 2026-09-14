"""Deterministic broker simulator. It cannot submit external orders."""
from dataclasses import dataclass, asdict


FEE = 0.0004
SLIPPAGE = 0.0005
STOP = 0.01
TAKE = 0.02


@dataclass
class VirtualPosition:
    symbol: str
    entry: float
    quantity: float
    opened_at: int
    stop: float
    take: float


class VirtualBroker:
    def __init__(self, initial_balance=1000.0):
        self.balance = float(initial_balance)
        self.initial_balance = float(initial_balance)
        self.positions = {}
        self.trades = []
        self.equity_curve = []

    def open(self, symbol, price, timestamp, allocation=0.2):
        if symbol in self.positions or price <= 0:
            return False
        value = min(self.balance, self.balance * allocation)
        entry = price * (1 + SLIPPAGE)
        self.positions[symbol] = VirtualPosition(
            symbol, entry, value / entry, timestamp,
            entry * (1 - STOP), entry * (1 + TAKE))
        return True

    def mark(self, symbol, candle, timestamp):
        position = self.positions.get(symbol)
        if position is None:
            return None
        exit_price = None
        reason = None
        if candle.open <= position.stop:
            exit_price, reason = candle.open, 'STOP_GAP'
        elif candle.open >= position.take:
            exit_price, reason = position.take, 'TAKE_PROFIT'
        elif candle.low <= position.stop:
            exit_price, reason = position.stop, 'STOP_LOSS'
        elif candle.high >= position.take:
            exit_price, reason = position.take, 'TAKE_PROFIT'
        if exit_price is None:
            return None
        sold = exit_price * (1 - SLIPPAGE)
        proceeds = position.quantity * sold * (1 - FEE)
        cost = position.quantity * position.entry * (1 + FEE)
        profit = proceeds - cost
        self.balance += profit
        self.trades.append({**asdict(position), 'exit_price': exit_price,
                            'exit_timestamp': timestamp, 'profit': profit,
                            'reason': reason})
        del self.positions[symbol]
        return self.trades[-1]

    def snapshot(self, prices, timestamp):
        equity = self.balance
        for symbol, position in self.positions.items():
            price = prices.get(symbol, position.entry)
            equity += position.quantity * price * (1 - SLIPPAGE) - position.quantity * position.entry
        point = {'timestamp': timestamp, 'balance': self.balance,
                 'equity': equity, 'open_positions': len(self.positions)}
        self.equity_curve.append(point)
        return point
