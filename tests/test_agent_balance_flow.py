from src.agent.agent_engine import AgentEngine
from src.agent.agent_config import AgentConfig


def test_agent_has_initial_balance():
    config = AgentConfig(
        initial_balance=1000.0
    )

    agent = AgentEngine(config=config)

    assert agent.balance == 1000.0


def test_agent_balance_changes_after_profitable_trade():
    config = AgentConfig(
        initial_balance=1000.0,
        risk_percent=5.0,
        risk_reward_ratio=2.0
    )

    agent = AgentEngine(config=config)

    agent.execute_trade(
        signal="BUY",
        entry_price=100.0,
        quantity=10.0,
        stop_loss=95.0,
        take_profit=110.0
    )

    result = agent.trading_engine.check_position(110.0)

    assert result is not None
    assert result["profit"] == 100.0
    assert agent.balance == 1100.0


def test_agent_balance_changes_after_losing_trade():
    config = AgentConfig(
        initial_balance=1000.0,
        risk_percent=5.0,
        risk_reward_ratio=2.0
    )

    agent = AgentEngine(config=config)

    agent.execute_trade(
        signal="BUY",
        entry_price=100.0,
        quantity=10.0,
        stop_loss=95.0,
        take_profit=110.0
    )

    result = agent.trading_engine.check_position(95.0)

    assert result is not None
    assert result["profit"] == -50.0
    assert agent.balance == 950.0