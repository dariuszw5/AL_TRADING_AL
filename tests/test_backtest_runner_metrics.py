from src.backtest.backtest_runner import BacktestRunner


class FakeBacktestResult:

    def get_profit_factor(self):
        return 2.0

    def get_average_win(self):
        return 15.0

    def get_average_loss(self):
        return 7.5

    def get_largest_win(self):
        return 20.0

    def get_largest_loss(self):
        return 10.0

    def get_expectancy(self):
        return 2.5


def test_backtest_runner_exposes_metrics():
    runner = BacktestRunner()

    runner.backtest_engine.get_backtest_result = (
        lambda: FakeBacktestResult()
    )

    assert runner.get_profit_factor() == 2.0
    assert runner.get_average_win() == 15.0
    assert runner.get_average_loss() == 7.5
    assert runner.get_largest_win() == 20.0
    assert runner.get_largest_loss() == 10.0
    assert runner.get_expectancy() == 2.5