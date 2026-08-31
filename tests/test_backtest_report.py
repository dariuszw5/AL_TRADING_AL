from src.backtest.backtest_runner import BacktestRunner
from src.backtest.backtest_report import BacktestReport
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


def create_runner():
    runner = BacktestRunner(
        symbol="BTCUSDT",
        interval="1m",
        limit=3,
        initial_balance=1000.0
    )

    runner.data_provider = FakeDataProvider()
    runner.load_data()
    runner.run()

    return runner


def test_backtest_report_has_data():
    runner = create_runner()

    report = BacktestReport(runner)

    data = report.get_data()

    assert data["symbol"] == "BTCUSDT"
    assert data["candles"] == 3


def test_backtest_report_returns_text():
    runner = create_runner()

    report = BacktestReport(runner)

    text = report.format()

    assert isinstance(text, str)
    assert "BACKTEST REPORT" in text
    assert "BTCUSDT" in text
    assert "Saldo początkowe" in text
    assert "Saldo końcowe" in text
    assert "Win rate" in text


def test_backtest_report_contains_statistics():
    runner = create_runner()

    report = BacktestReport(runner)

    text = report.format()

    assert "Liczba transakcji" in text
    assert "Wygrane" in text
    assert "Przegrane" in text
    assert "Max drawdown" in text