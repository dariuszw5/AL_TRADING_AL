from src.backtest.backtest_runner import BacktestRunner
from src.data.candle import Candle


def test_backtest_runner_defaults_to_api():
    runner = BacktestRunner()

    assert runner.data_source == "api"


def test_backtest_runner_accepts_file_data_source():
    runner = BacktestRunner(
        data_source="file"
    )

    assert runner.data_source == "file"


def test_backtest_runner_loads_local_file(monkeypatch):
    runner = BacktestRunner(
        data_source="file"
    )

    candles = [
        Candle(
            timestamp=1000,
            open=100.0,
            high=105.0,
            low=95.0,
            close=102.0,
            volume=10.0
        ),
        Candle(
            timestamp=1060,
            open=102.0,
            high=108.0,
            low=101.0,
            close=107.0,
            volume=12.0
        )
    ]

    monkeypatch.setattr(
        runner.data_provider,
        "load_candles",
        lambda file_path: candles
    )

    result = runner.load_data()

    assert len(result) == 2
    assert result[0].timestamp == 1000
    assert result[1].timestamp == 1060