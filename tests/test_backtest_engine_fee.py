import pytest


from src.backtest.backtest_engine import BacktestEngine


class FakeAgent:
    def __init__(self):
        self.index = 0

    def run_cycle(self, candles):
        self.index += 1

        if self.index == 1:
            return {
                "signal": "BUY",
                "position": None,
                "result": None
            }

        if self.index == 2:
            return {
                "signal": "HOLD",
                "position": None,
                "result": {
                    "side": "BUY",
                    "entry_price": 100.0,
                    "exit_price": 110.0,
                    "quantity": 1.0,
                    "profit": 10.0
                }
            }

        return {
            "signal": "HOLD",
            "position": None,
            "result": None
        }


def test_backtest_engine_without_fee_keeps_profit():
    engine = BacktestEngine(
        agent=FakeAgent(),
        initial_balance=1000.0,
        trading_fee=0.0
    )

    engine.run([
        {"close": 100},
        {"close": 110}
    ])

    assert engine.get_total_profit() == 10.0


def test_backtest_engine_applies_trading_fee():
    engine = BacktestEngine(
        agent=FakeAgent(),
        initial_balance=1000.0,
        trading_fee=0.001
    )

    engine.run([
        {"close": 100},
        {"close": 110}
    ])

    assert engine.get_total_profit() == pytest.approx(9.79)


def test_backtest_engine_stores_fee_in_trade():
    engine = BacktestEngine(
        agent=FakeAgent(),
        initial_balance=1000.0,
        trading_fee=0.001
    )

    engine.run([
        {"close": 100},
        {"close": 110}
    ])

    trades = engine.get_backtest_result().get_trades()

    assert len(trades) == 1
    assert trades[0]["gross_profit"] == 10.0
    assert trades[0]["fee"] == 0.21
    assert trades[0]["profit"] == 9.79