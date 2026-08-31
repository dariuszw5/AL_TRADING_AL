from src.backtest.backtest_result import BacktestResult


def create_result():
    result = BacktestResult(initial_balance=1000.0)

    result.add_trade({
        "side": "BUY",
        "profit": 10.0
    })

    result.add_trade({
        "side": "SELL",
        "profit": -5.0
    })

    result.add_trade({
        "side": "BUY",
        "profit": 20.0
    })

    result.add_trade({
        "side": "SELL",
        "profit": -10.0
    })

    return result


def test_profit_factor():
    result = create_result()

    assert result.get_profit_factor() == 2.0


def test_average_win():
    result = create_result()

    assert result.get_average_win() == 15.0


def test_average_loss():
    result = create_result()

    assert result.get_average_loss() == 7.5


def test_largest_win():
    result = create_result()

    assert result.get_largest_win() == 20.0


def test_largest_loss():
    result = create_result()

    assert result.get_largest_loss() == 10.0


def test_expectancy():
    result = create_result()

    assert result.get_expectancy() == 3.75
