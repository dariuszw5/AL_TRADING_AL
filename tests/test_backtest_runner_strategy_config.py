from src.backtest.backtest_runner import BacktestRunner


def test_backtest_runner_accepts_strategy_parameters():
    runner = BacktestRunner(
        buy_rsi=25.0,
        sell_rsi=75.0,
        min_difference=2.0
    )

    assert runner.buy_rsi == 25.0
    assert runner.sell_rsi == 75.0
    assert runner.min_difference == 2.0


def test_backtest_runner_passes_strategy_parameters_to_agent():
    runner = BacktestRunner(
        buy_rsi=25.0,
        sell_rsi=75.0,
        min_difference=2.0
    )

    assert runner.agent.config.buy_rsi == 25.0
    assert runner.agent.config.sell_rsi == 75.0
    assert runner.agent.config.min_difference == 2.0
    