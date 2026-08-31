from src.backtest.backtest_runner import BacktestRunner


def test_backtest_runner_returns_trades():
    runner = BacktestRunner(
        symbol="BTCUSDT",
        interval="1m",
        limit=10,
        initial_balance=1000.0
    )

    runner.backtest_engine.get_backtest_result().add_trade({
        "side": "BUY",
        "entry_price": 100.0,
        "exit_price": 110.0,
        "quantity": 1.0,
        "profit": 10.0
    })

    trades = runner.get_trades()

    assert len(trades) == 1
    assert trades[0]["side"] == "BUY"
    assert trades[0]["profit"] == 10.0
