from src.trading.trade_manager import TradeManager


def test_trade_manager_exists():
    manager = TradeManager()

    assert manager is not None


def test_open_position():
    manager = TradeManager()

    position = manager.open_position(
        side="BUY",
        entry_price=100.0,
        quantity=2.0,
        stop_loss=95.0,
        take_profit=110.0
    )

    assert position["side"] == "BUY"
    assert position["entry_price"] == 100.0
    assert position["quantity"] == 2.0
    assert position["stop_loss"] == 95.0
    assert position["take_profit"] == 110.0


def test_close_position():
    manager = TradeManager()

    manager.open_position(
        side="BUY",
        entry_price=100.0,
        quantity=2.0,
        stop_loss=95.0,
        take_profit=110.0
    )

    result = manager.close_position(exit_price=110.0)

    assert result["side"] == "BUY"
    assert result["entry_price"] == 100.0
    assert result["exit_price"] == 110.0
    assert result["quantity"] == 2.0
    assert result["profit"] == 20.0


def test_position_is_closed():
    manager = TradeManager()

    manager.open_position(
        side="BUY",
        entry_price=100.0,
        quantity=2.0,
        stop_loss=95.0,
        take_profit=110.0
    )

    manager.close_position(exit_price=110.0)

    assert manager.position is None


def test_stop_loss_closes_buy_position():
    manager = TradeManager()

    manager.open_position(
        side="BUY",
        entry_price=100.0,
        quantity=2.0,
        stop_loss=95.0,
        take_profit=110.0
    )

    result = manager.check_exit(95.0)

    assert result["exit_price"] == 95.0
    assert result["profit"] == -10.0
    assert manager.position is None


def test_take_profit_closes_buy_position():
    manager = TradeManager()

    manager.open_position(
        side="BUY",
        entry_price=100.0,
        quantity=2.0,
        stop_loss=95.0,
        take_profit=110.0
    )

    result = manager.check_exit(110.0)

    assert result["exit_price"] == 110.0
    assert result["profit"] == 20.0
    assert manager.position is None


def test_position_remains_open_between_levels():
    manager = TradeManager()

    manager.open_position(
        side="BUY",
        entry_price=100.0,
        quantity=2.0,
        stop_loss=95.0,
        take_profit=110.0
    )

    result = manager.check_exit(105.0)

    assert result is None
    assert manager.position is not None

def test_trade_history_after_closing_position():
    manager = TradeManager()

    manager.open_position(
        side="BUY",
        entry_price=100.0,
        quantity=2.0,
        stop_loss=95.0,
        take_profit=110.0
    )

    result = manager.close_position(exit_price=110.0)

    assert result is not None
    assert hasattr(manager, "trade_history")
    assert len(manager.trade_history) == 1
    assert manager.trade_history[0]["side"] == "BUY"
    assert manager.trade_history[0]["profit"] == 20.0


def test_trade_statistics():
    manager = TradeManager()

    manager.open_position(
        side="BUY",
        entry_price=100.0,
        quantity=2.0,
        stop_loss=95.0,
        take_profit=110.0
    )

    manager.close_position(exit_price=110.0)

    manager.open_position(
        side="BUY",
        entry_price=100.0,
        quantity=2.0,
        stop_loss=95.0,
        take_profit=110.0
    )

    manager.close_position(exit_price=95.0)

    statistics = manager.get_statistics()

    assert statistics["total_trades"] == 2
    assert statistics["winning_trades"] == 1
    assert statistics["losing_trades"] == 1
    assert statistics["win_rate"] == 50.0
    assert statistics["total_profit"] == 10.0