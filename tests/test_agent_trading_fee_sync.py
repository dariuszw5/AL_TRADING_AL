import pytest

from src.agent.agent_engine import AgentEngine
from src.agent.agent_config import AgentConfig


def test_agent_balance_uses_net_profit_after_fee():
    agent = AgentEngine(
        config=AgentConfig(
            initial_balance=1000.0,
            trading_fee=0.001
        )
    )

    agent.execute_trade(
        signal="BUY",
        entry_price=100.0,
        quantity=1.0,
        stop_loss=95.0,
        take_profit=110.0
    )

    result = agent.trading_engine.check_position(
        110.0
    )

    assert result is not None
    assert result["gross_profit"] == 10.0
    assert result["fee"] == pytest.approx(0.21)
    assert result["profit"] == pytest.approx(9.79)
    assert agent.balance == pytest.approx(1009.79)


def test_agent_balance_without_fee_is_unchanged():
    agent = AgentEngine(
        config=AgentConfig(
            initial_balance=1000.0,
            trading_fee=0.0
        )
    )

    agent.execute_trade(
        signal="BUY",
        entry_price=100.0,
        quantity=1.0,
        stop_loss=95.0,
        take_profit=110.0
    )

    result = agent.trading_engine.check_position(
        110.0
    )

    assert result is not None
    assert result["gross_profit"] == 10.0
    assert result["fee"] == 0.0
    assert result["profit"] == 10.0
    assert agent.balance == pytest.approx(1010.0)


def test_agent_closed_trade_contains_fee_information():
    agent = AgentEngine(
        config=AgentConfig(
            initial_balance=1000.0,
            trading_fee=0.001
        )
    )

    agent.execute_trade(
        signal="BUY",
        entry_price=100.0,
        quantity=1.0,
        stop_loss=95.0,
        take_profit=110.0
    )

    result = agent.trading_engine.check_position(
        110.0
    )

    assert result["gross_profit"] == 10.0
    assert result["fee"] == pytest.approx(0.21)
    assert result["profit"] == pytest.approx(9.79)