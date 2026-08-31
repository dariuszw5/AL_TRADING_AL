from src.agent.agent_engine import AgentEngine
from src.agent.agent_config import AgentConfig


def test_agent_records_closed_trade_loss_in_risk_guard():
    config = AgentConfig(
        initial_balance=1000.0,
        risk_percent=5.0
    )

    agent = AgentEngine(config=config)

    agent.execute_trade(
        signal="BUY",
        entry_price=100.0,
        quantity=2.0,
        stop_loss=95.0,
        take_profit=110.0
    )

    result = agent.trading_engine.check_position(90.0)

    assert result is not None
    assert result["profit"] == -10.0
    assert agent.risk_guard.daily_loss == 10.0
    assert agent.risk_guard.can_trade() is True


def test_agent_blocks_trading_after_daily_loss_limit():
    config = AgentConfig(
        initial_balance=1000.0,
        risk_percent=5.0
    )

    agent = AgentEngine(config=config)

    agent.execute_trade(
        signal="BUY",
        entry_price=100.0,
        quantity=20.0,
        stop_loss=95.0,
        take_profit=110.0
    )

    result = agent.trading_engine.check_position(90.0)

    assert result is not None
    assert result["profit"] == -100.0
    assert agent.risk_guard.daily_loss == 100.0
    assert agent.risk_guard.can_trade() is False
