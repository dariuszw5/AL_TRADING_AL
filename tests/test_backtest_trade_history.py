from src.backtest.backtest_result import BacktestResult


def test_backtest_result_returns_trade_history():
    result = BacktestResult(initial_balance=1000.0)

    trade = {
        "side": "BUY",
        "entry_price": 100.0,
        "exit_price": 110.0,
        "quantity": 1.0,
        "profit": 10.0
    }

    result.add_trade(trade)

    trades = result.get_trades()

    assert len(trades) == 1
    assert trades[0]["side"] == "BUY"
    assert trades[0]["profit"] == 10.0


def test_backtest_result_returns_copy_of_trade_history():
    result = BacktestResult(initial_balance=1000.0)

    result.add_trade({
        "side": "BUY",
        "profit": 10.0
    })

    trades = result.get_trades()

    trades.clear()

    assert result.get_trade_count() == 1
