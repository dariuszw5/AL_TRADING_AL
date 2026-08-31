from src.agent.agent_engine import AgentEngine
from src.agent.trade_history import TradeHistory


def test_agent_engine_has_trade_history():
    engine = AgentEngine()

    assert hasattr(engine, "trade_history")
    assert isinstance(engine.trade_history, TradeHistory)


def test_trade_history_is_empty_initially():
    engine = AgentEngine()

    assert engine.trade_history.count() == 0


def test_opened_trade_is_saved_to_history():
    engine = AgentEngine()

    result = engine.execute_trade(
        signal="BUY",
        entry_price=100.0,
        quantity=1.0,
        stop_loss=95.0,
        take_profit=110.0
    )

    assert result["status"] == "OPEN"
    assert engine.trade_history.count() == 1


def test_rejected_trade_is_not_saved():
    engine = AgentEngine()

    result = engine.execute_trade(
        signal="INVALID",
        entry_price=100.0,
        quantity=1.0,
        stop_loss=95.0,
        take_profit=110.0
    )

    assert result["status"] == "REJECTED"
    assert engine.trade_history.count() == 0


def test_second_trade_is_not_saved():
    engine = AgentEngine()

    engine.execute_trade(
        signal="BUY",
        entry_price=100.0,
        quantity=1.0,
        stop_loss=95.0,
        take_profit=110.0
    )

    result = engine.execute_trade(
        signal="BUY",
        entry_price=101.0,
        quantity=1.0,
        stop_loss=96.0,
        take_profit=112.0
    )

    assert result["status"] == "ALREADY_OPEN"
    assert engine.trade_history.count() == 1