from src.backtest.backtest_runner import BacktestRunner


def test_backtest_runner_accepts_trading_fee():
    runner = BacktestRunner(
        trading_fee=0.001
    )

    assert runner.trading_fee == 0.001


def test_backtest_runner_passes_trading_fee_to_agent():
    runner = BacktestRunner(
        trading_fee=0.001
    )

    assert runner.agent.config.trading_fee == 0.001


def test_backtest_runner_passes_trading_fee_to_backtest_engine():
    runner = BacktestRunner(
        trading_fee=0.001
    )

    assert runner.backtest_engine.trading_fee == 0.001