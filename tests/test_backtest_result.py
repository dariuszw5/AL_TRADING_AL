from src.backtest.backtest_result import BacktestResult


def test_backtest_result_initial_balance():
    result = BacktestResult()

    assert result.get_balance() == 1000.0
    assert result.get_total_profit() == 0.0


def test_backtest_result_adds_profit():
    result = BacktestResult()

    result.add_trade({
        "profit": 100.0
    })

    assert result.get_balance() == 1100.0
    assert result.get_total_profit() == 100.0


def test_backtest_result_adds_loss():
    result = BacktestResult()

    result.add_trade({
        "profit": -50.0
    })

    assert result.get_balance() == 950.0
    assert result.get_total_profit() == -50.0


def test_backtest_result_counts_trades():
    result = BacktestResult()

    result.add_trade({
        "profit": 100.0
    })

    result.add_trade({
        "profit": -50.0
    })

    assert result.get_trade_count() == 2


def test_backtest_result_counts_winners():
    result = BacktestResult()

    result.add_trade({
        "profit": 100.0
    })

    result.add_trade({
        "profit": -50.0
    })

    assert result.get_winning_trades() == 1


def test_backtest_result_counts_losers():
    result = BacktestResult()

    result.add_trade({
        "profit": 100.0
    })

    result.add_trade({
        "profit": -50.0
    })

    assert result.get_losing_trades() == 1


def test_backtest_result_win_rate():
    result = BacktestResult()

    result.add_trade({
        "profit": 100.0
    })

    result.add_trade({
        "profit": -50.0
    })

    assert result.get_win_rate() == 50.0


def test_backtest_result_max_drawdown():
    result = BacktestResult()

    result.add_trade({
        "profit": 100.0
    })

    result.add_trade({
        "profit": -150.0
    })

    assert result.get_max_drawdown() == 150.0


def test_backtest_result_equity_curve():
    result = BacktestResult()

    result.add_trade({
        "profit": 100.0
    })

    result.add_trade({
        "profit": -50.0
    })

    assert result.get_equity_curve() == [
        1000.0,
        1100.0,
        1050.0
    ]