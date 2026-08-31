from src.trading.paper_trading import PaperTrading


def test_paper_trading_exists():
    engine = PaperTrading()

    assert engine is not None


def test_paper_trading_starts_with_zero_balance():
    engine = PaperTrading(initial_balance=1000.0)

    assert engine.balance == 1000.0
    assert engine.equity == 1000.0


def test_paper_trading_buy_and_take_profit():
    engine = PaperTrading(initial_balance=1000.0)

    engine.open_position(
        side="BUY",
        entry_price=100.0,
        quantity=2.0,
        stop_loss=95.0,
        take_profit=110.0
    )

    result = engine.update_price(110.0)

    assert result is not None
    assert result["profit"] == 20.0
    assert engine.position is None
    assert engine.balance == 1020.0
    assert engine.equity == 1020.0


def test_paper_trading_buy_and_stop_loss():
    engine = PaperTrading(initial_balance=1000.0)

    engine.open_position(
        side="BUY",
        entry_price=100.0,
        quantity=2.0,
        stop_loss=95.0,
        take_profit=110.0
    )

    result = engine.update_price(95.0)

    assert result is not None
    assert result["profit"] == -10.0
    assert engine.position is None
    assert engine.balance == 990.0
    assert engine.equity == 990.0


def test_paper_trading_equity_with_open_position():
    engine = PaperTrading(initial_balance=1000.0)

    engine.open_position(
        side="BUY",
        entry_price=100.0,
        quantity=2.0,
        stop_loss=95.0,
        take_profit=110.0
    )

    engine.update_price(105.0)

    assert engine.position is not None
    assert engine.balance == 1000.0
    assert engine.equity == 1010.0