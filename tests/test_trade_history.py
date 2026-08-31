from src.agent.trade_history import TradeHistory


def test_trade_history_exists():
    history = TradeHistory()

    assert history is not None


def test_trade_history_starts_empty():
    history = TradeHistory()

    assert history.get_trades() == []


def test_trade_history_can_add_trade():
    history = TradeHistory()

    trade = {
        "signal": "BUY",
        "entry_price": 100.0,
        "quantity": 1.0
    }

    history.add_trade(trade)

    assert len(history.get_trades()) == 1


def test_trade_history_returns_trade():
    history = TradeHistory()

    trade = {
        "signal": "BUY",
        "entry_price": 100.0,
        "quantity": 1.0
    }

    history.add_trade(trade)

    result = history.get_trades()

    assert result[0] == trade


def test_trade_history_counts_trades():
    history = TradeHistory()

    history.add_trade({"signal": "BUY"})
    history.add_trade({"signal": "SELL"})

    assert history.count() == 2