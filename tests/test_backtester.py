from src.backtest.backtester import Backtester


def test_backtester():
    backtester = Backtester()

    result = backtester.run([])

    assert result["trades"] == 0
    assert result["profit"] == 0

def test_profitable_trade():
    backtester = Backtester()

    signals = [
        ("BUY", 100.0),
        ("HOLD", 105.0),
        ("SELL", 110.0)
    ]

    result = backtester.run(signals)

    assert result["trades"] == 1
    assert result["profit"] == 10.0

def test_losing_trade():
    backtester = Backtester()

    signals = [
        ("BUY", 100.0),
        ("HOLD", 95.0),
        ("SELL", 90.0)
    ]

    result = backtester.run(signals)

    assert result["trades"] == 1
    assert result["profit"] == -10.0


def test_return_percentage():
    backtester = Backtester(initial_balance=1000.0)

    signals = [
        ("BUY", 100.0),
        ("SELL", 110.0)
    ]

    result = backtester.run(signals)

    assert result["trades"] == 1
    assert result["profit"] == 10.0
    assert result["balance"] == 1010.0
    assert result["return_percent"] == 1.0


def test_trade_statistics():
    backtester = Backtester(initial_balance=1000.0)

    signals = [
        ("BUY", 100.0),
        ("SELL", 110.0),
        ("BUY", 100.0),
        ("SELL", 90.0),
        ("BUY", 100.0),
        ("SELL", 120.0)
    ]

    result = backtester.run(signals)

    assert result["trades"] == 3
    assert result["winning_trades"] == 2
    assert result["losing_trades"] == 1
    assert result["win_rate"] == 66.67


def test_max_drawdown():
    backtester = Backtester(initial_balance=1000.0)

    signals = [
        ("BUY", 100.0),
        ("SELL", 90.0),
        ("BUY", 100.0),
        ("SELL", 110.0),
        ("BUY", 100.0),
        ("SELL", 105.0)
    ]

    result = backtester.run(signals)

    assert result["max_drawdown"] == 1.0