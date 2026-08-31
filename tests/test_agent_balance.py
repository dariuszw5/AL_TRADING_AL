from src.agent.agent_engine import AgentEngine
from src.agent.agent_config import AgentConfig


def test_agent_starts_with_initial_balance():
    config = AgentConfig(
        initial_balance=1000.0
    )

    agent = AgentEngine(config=config)

    assert agent.balance == 1000.0


def test_agent_balance_increases_after_profit():
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

    result = agent.trading_engine.check_position(110.0)

    assert result is not None
    assert result["profit"] == 20.0
    assert agent.balance == 1020.0


def test_agent_balance_decreases_after_loss():
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
    assert agent.balance == 990.0


def test_agent_uses_current_balance_for_position_size():
    config = AgentConfig(
        initial_balance=1000.0,
        risk_percent=5.0,
        risk_reward_ratio=2.0
    )

    agent = AgentEngine(config=config)

    agent.balance = 1200.0

    setup = agent.trading_engine.generate_trade_setup(
        signal="BUY",
        entry_price=100.0,
        risk_percent=5.0,
        risk_reward_ratio=2.0,
        balance=agent.balance
    )

    assert setup["position_size"] == 12.0