from src.trading.trade_manager import TradeManager


def test_trade_manager_stores_entry_timestamp():
    manager = TradeManager()

    result = manager.open_position(
        side="BUY",
        entry_price=100.0,
        quantity=1.0,
        stop_loss=95.0,
        take_profit=110.0,
        entry_timestamp=1000
    )

    assert result is not None
    assert result["entry_timestamp"] == 1000


def test_trade_manager_stores_exit_timestamp():
    manager = TradeManager()

    manager.open_position(
        side="BUY",
        entry_price=100.0,
        quantity=1.0,
        stop_loss=95.0,
        take_profit=110.0,
        entry_timestamp=1000
    )

    result = manager.close_position(
        exit_price=110.0,
        exit_timestamp=1060
    )

    assert result is not None
    assert result["entry_timestamp"] == 1000
    assert result["exit_timestamp"] == 1060


def test_trade_manager_default_timestamps_are_none():
    manager = TradeManager()

    result = manager.open_position(
        side="BUY",
        entry_price=100.0,
        quantity=1.0,
        stop_loss=95.0,
        take_profit=110.0
    )

    assert result["entry_timestamp"] is None

    result = manager.close_position(
        exit_price=110.0
    )

    assert result["exit_timestamp"] is None