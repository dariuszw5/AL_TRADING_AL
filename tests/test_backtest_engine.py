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
                    "profit": 10.0
                }
            }

        if self.index == 3:
            return {
                "signal": "HOLD",
                "position": None,
                "result": {
                    "profit": -5.0
                }
            }

        return {
            "signal": "HOLD",
            "position": None,
            "result": None
        }


def test_backtest_engine_can_run():
    agent = FakeAgent()
    engine = BacktestEngine(agent)

    candles = [
        {"close": 100},
        {"close": 105},
        {"close": 95}
    ]

    results = engine.run(candles)

    assert len(results) == 3


def test_backtest_engine_counts_trades():
    agent = FakeAgent()
    engine = BacktestEngine(agent)

    candles = [
        {"close": 100},
        {"close": 105},
        {"close": 95}
    ]

    engine.run(candles)

    assert engine.get_trade_count() == 2


def test_backtest_engine_calculates_profit():
    agent = FakeAgent()
    engine = BacktestEngine(agent)

    candles = [
        {"close": 100},
        {"close": 105},
        {"close": 95}
    ]

    engine.run(candles)

    assert engine.get_total_profit() == 5.0


def test_backtest_engine_counts_winners():
    agent = FakeAgent()
    engine = BacktestEngine(agent)

    candles = [
        {"close": 100},
        {"close": 105},
        {"close": 95}
    ]

    engine.run(candles)

    assert engine.get_winning_trades() == 1


def test_backtest_engine_counts_losers():
    agent = FakeAgent()
    engine = BacktestEngine(agent)

    candles = [
        {"close": 100},
        {"close": 105},
        {"close": 95}
    ]

    engine.run(candles)

    assert engine.get_losing_trades() == 1


def test_backtest_engine_calculates_win_rate():
    agent = FakeAgent()
    engine = BacktestEngine(agent)

    candles = [
        {"close": 100},
        {"close": 105},
        {"close": 95}
    ]

    engine.run(candles)

    assert engine.get_win_rate() == 50.0