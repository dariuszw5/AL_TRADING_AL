from src.backtest.backtest_engine import BacktestEngine


class FakeTradeManager:
    def __init__(self):
        self.position = {
            "side": "BUY",
            "entry_price": 100.0,
            "quantity": 1.0,
            "stop_loss": 90.0,
            "take_profit": 120.0
        }

    def close_position(self, exit_price):
        if self.position is None:
            return None

        position = self.position

        profit = (
            exit_price - position["entry_price"]
        ) * position["quantity"]

        result = {
            "side": position["side"],
            "entry_price": position["entry_price"],
            "exit_price": exit_price,
            "quantity": position["quantity"],
            "stop_loss": position["stop_loss"],
            "take_profit": position["take_profit"],
            "profit": profit
        }

        self.position = None

        return result


class FakeTradingEngine:
    def __init__(self):
        self.trade_manager = FakeTradeManager()

    def check_position(self, current_price):
        return None


class FakeAgent:
    def __init__(self):
        self.trading_engine = FakeTradingEngine()

    def run_cycle(self, candles):
        return {
            "signal": "HOLD",
            "position": self.trading_engine.trade_manager.position,
            "result": None
        }


def test_backtest_auto_closes_last_position():
    agent = FakeAgent()
    engine = BacktestEngine(agent)

    engine.run([
        {"close": 100.0},
        {"close": 105.0}
    ])

    engine.close(105.0)

    assert engine.get_trade_count() == 1
    assert engine.get_total_profit() == 5.0


def test_backtest_auto_close_updates_balance():
    agent = FakeAgent()
    engine = BacktestEngine(agent)

    engine.run([
        {"close": 100.0},
        {"close": 105.0}
    ])

    engine.close(105.0)

    assert engine.get_balance() == 1005.0


def test_backtest_auto_close_removes_position():
    agent = FakeAgent()
    engine = BacktestEngine(agent)

    engine.run([
        {"close": 100.0},
        {"close": 105.0}
    ])

    engine.close(105.0)

    assert (
        agent.trading_engine.trade_manager.position
        is None
    )