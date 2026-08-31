from src.backtest.backtest_runner import BacktestRunner
from src.data.candle import Candle


class FakeDataProvider:
    def get_historical_candles(
        self,
        symbol="BTCUSDT",
        interval="1m",
        limit=1000
    ):
        return [
            Candle(
                timestamp=1,
                open=100.0,
                high=105.0,
                low=95.0,
                close=102.0,
                volume=10.0
            ),
            Candle(
                timestamp=2,
                open=102.0,
                high=108.0,
                low=100.0,
                close=106.0,
                volume=12.0
            ),
            Candle(
                timestamp=3,
                open=106.0,
                high=110.0,
                low=103.0,
                close=109.0,
                volume=15.0
            )
        ]


def test_backtest_runner_has_configuration():
    runner = BacktestRunner(
        symbol="BTCUSDT",
        interval="1m",
        limit=3,
        initial_balance=1000.0
    )

    assert runner.symbol == "BTCUSDT"
    assert runner.interval == "1m"
    assert runner.limit == 3
    assert runner.initial_balance == 1000.0


def test_backtest_runner_loads_data():
    runner = BacktestRunner(
        symbol="BTCUSDT",
        interval="1m",
        limit=3
    )

    runner.data_provider = FakeDataProvider()

    candles = runner.load_data()

    assert len(candles) == 3
    assert isinstance(candles[0], Candle)


def test_backtest_runner_runs_backtest():
    runner = BacktestRunner(
        symbol="BTCUSDT",
        interval="1m",
        limit=3
    )

    runner.data_provider = FakeDataProvider()

    runner.load_data()

    results = runner.run()

    assert isinstance(results, list)
    assert len(results) == 3


def test_backtest_runner_returns_summary():
    runner = BacktestRunner(
        symbol="BTCUSDT",
        interval="1m",
        limit=3
    )

    runner.data_provider = FakeDataProvider()

    runner.load_data()
    runner.run()

    summary = runner.get_summary()

    assert summary["symbol"] == "BTCUSDT"
    assert summary["interval"] == "1m"
    assert summary["candles"] == 3
    assert summary["initial_balance"] == 1000.0
    assert summary["final_balance"] >= 0
    assert summary["trades"] >= 0
    assert summary["total_profit"] is not None