from src.backtest.backtest_runner import BacktestRunner


def test_backtest_runner_loads_real_benchmark_file():
    runner = BacktestRunner(
        symbol="BTCUSDT",
        interval="1m",
        limit=5000,
        data_source="file"
    )

    candles = runner.load_data()

    assert len(candles) == 5000
    assert candles[0].timestamp == 1787262840000
    assert candles[-1].timestamp == 1787562780000
