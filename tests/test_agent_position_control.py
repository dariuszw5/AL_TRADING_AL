from src.agent.agent_engine import AgentEngine


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
        take_profit=111.0
    )

    assert first is not None
    assert first["status"] == "OPEN"

    assert second is not None
    assert second["status"] == "ALREADY_OPEN"


def test_agent_can_close_position():
    engine = AgentEngine()

    engine.execute_trade(
        signal="BUY",
        entry_price=100.0,
        quantity=1.0,
        stop_loss=95.0,
        take_profit=110.0
    )

    result = engine.run_cycle([
        {
            "timestamp": 1,
            "open": 109.0,
            "high": 111.0,
            "low": 108.0,
            "close": 110.0,
            "volume": 10.0
        }
    ])

    assert result is not None
    