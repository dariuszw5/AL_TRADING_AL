from src.agent.agent_engine import AgentEngine


def test_agent_rejects_trade_when_stopped():
    engine = AgentEngine()

    engine.stop()

    result = engine.execute_trade(
        signal="BUY",
        entry_price=100.0,
        quantity=1.0,
        stop_loss=95.0,
        take_profit=110.0
    )

    assert result["status"] == "REJECTED"


def test_agent_does_not_open_second_position():
    engine = AgentEngine()

    first = engine.execute_trade(
        signal="BUY",
        entry_price=100.0,
        quantity=1.0,
        stop_loss=95.0,
        take_profit=110.0
    )

    second = engine.execute_trade(
        signal="BUY",
        entry_price=101.0,
        quantity=1.0,
        stop_loss=96.0,
        take_profit=112.0
    )

    assert first["status"] == "OPEN"
    assert second["status"] == "ALREADY_OPEN"


def test_agent_remains_stopped():
    engine = AgentEngine()

    engine.stop()

    assert engine.state == "STOPPED"

    engine.state = "TRADING"

    assert engine.state == "STOPPED"
    