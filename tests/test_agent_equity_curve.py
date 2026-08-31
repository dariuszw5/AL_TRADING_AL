from src.agent.agent_engine import AgentEngine
from src.agent.agent_config import AgentConfig


def test_agent_equity_curve_starts_with_initial_balance():
    agent = AgentEngine(
        config=AgentConfig(
            initial_balance=1000.0
        )
    )

    assert agent.get_equity_curve() == [1000.0]


def test_agent_equity_curve_records_market_updates():
    agent = AgentEngine(
        config=AgentConfig(
            initial_balance=1000.0
        )
    )

    agent.update_market_price(100.0)
    agent.update_market_price(105.0)
    agent.update_market_price(102.0)

    curve = agent.get_equity_curve()

    assert curve == [
        1000.0,
        1000.0,
        1000.0,
        1000.0
    ]


def test_agent_equity_curve_records_open_position_equity():
    agent = AgentEngine(
        config=AgentConfig(
            initial_balance=1000.0
        )
    )

    agent.execute_trade(
        signal="BUY",
        entry_price=100.0,
        quantity=10.0,
        stop_loss=90.0,
        take_profit=120.0
    )

    agent.update_market_price(105.0)
    agent.update_market_price(110.0)

    curve = agent.get_equity_curve()

    assert curve[-2] == 1050.0
    assert curve[-1] == 1100.0


def test_agent_equity_curve_records_realized_profit():
    agent = AgentEngine(
        config=AgentConfig(
            initial_balance=1000.0
        )
    )

    agent.execute_trade(
        signal="BUY",
        entry_price=100.0,
        quantity=10.0,
        stop_loss=95.0,
        take_profit=110.0
    )

    agent.trading_engine.check_position(110.0)

    curve = agent.get_equity_curve()

    assert curve[-1] == 1100.0
