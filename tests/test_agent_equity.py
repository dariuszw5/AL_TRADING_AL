from src.agent.agent_engine import AgentEngine
from src.agent.agent_config import AgentConfig


def test_agent_equity_starts_at_initial_balance():
    config = AgentConfig(
        initial_balance=1000.0
    )

    agent = AgentEngine(config=config)

    assert agent.get_equity() == 1000.0


def test_agent_equity_equals_balance_without_open_position():
    config = AgentConfig(
        initial_balance=1000.0
    )

    agent = AgentEngine(config=config)

    assert agent.balance == 1000.0
    assert agent.get_equity() == 1000.0


def test_agent_peak_balance_starts_at_initial_balance():
    config = AgentConfig(
        initial_balance=1000.0
    )

    agent = AgentEngine(config=config)

    assert agent.get_peak_balance() == 1000.0


def test_agent_drawdown_starts_at_zero():
    config = AgentConfig(
        initial_balance=1000.0
    )

    agent = AgentEngine(config=config)

    assert agent.get_drawdown() == 0.0


def test_agent_max_drawdown_starts_at_zero():
    config = AgentConfig(
        initial_balance=1000.0
    )

    agent = AgentEngine(config=config)

    assert agent.get_max_drawdown() == 0.0


def test_agent_peak_balance_updates_after_profit():
    config = AgentConfig(
        initial_balance=1000.0
    )

    agent = AgentEngine(config=config)

    agent.execute_trade(
        signal="BUY",
        entry_price=100.0,
        quantity=10.0,
        stop_loss=95.0,
        take_profit=110.0
    )

    agent.trading_engine.check_position(110.0)

    assert agent.balance == 1100.0
    assert agent.get_peak_balance() == 1100.0
    assert agent.get_drawdown() == 0.0


def test_agent_drawdown_after_loss():
    config = AgentConfig(
        initial_balance=1000.0
    )

    agent = AgentEngine(config=config)

    agent.execute_trade(
        signal="BUY",
        entry_price=100.0,
        quantity=10.0,
        stop_loss=95.0,
        take_profit=110.0
    )

    agent.trading_engine.check_position(95.0)

    assert agent.balance == 950.0
    assert agent.get_peak_balance() == 1000.0
    assert agent.get_drawdown() == 50.0
    assert agent.get_max_drawdown() == 50.0


def test_agent_max_drawdown_keeps_previous_maximum():
    config = AgentConfig(
        initial_balance=1000.0,
        risk_percent=10.0
    )

    agent = AgentEngine(config=config)

    agent.execute_trade(
        signal="BUY",
        entry_price=100.0,
        quantity=10.0,
        stop_loss=95.0,
        take_profit=110.0
    )

    agent.trading_engine.check_position(95.0)

    agent.execute_trade(
        signal="BUY",
        entry_price=100.0,
        quantity=10.0,
        stop_loss=95.0,
        take_profit=110.0
    )

    agent.trading_engine.check_position(95.0)

    assert agent.balance == 900.0
    assert agent.get_peak_balance() == 1000.0
    assert agent.get_drawdown() == 100.0
    assert agent.get_max_drawdown() == 100.0


def test_agent_equity_includes_unrealized_profit_for_buy():
    config = AgentConfig(
        initial_balance=1000.0
    )

    agent = AgentEngine(config=config)

    agent.execute_trade(
        signal="BUY",
        entry_price=100.0,
        quantity=10.0,
        stop_loss=95.0,
        take_profit=110.0
    )

    agent.update_market_price(105.0)

    assert agent.balance == 1000.0
    assert agent.get_equity() == 1050.0


def test_agent_equity_includes_unrealized_loss_for_buy():
    config = AgentConfig(
        initial_balance=1000.0
    )

    agent = AgentEngine(config=config)

    agent.execute_trade(
        signal="BUY",
        entry_price=100.0,
        quantity=10.0,
        stop_loss=90.0,
        take_profit=120.0
    )

    agent.update_market_price(95.0)

    assert agent.balance == 1000.0
    assert agent.get_equity() == 950.0


def test_agent_equity_includes_unrealized_profit_for_sell():
    config = AgentConfig(
        initial_balance=1000.0
    )

    agent = AgentEngine(config=config)

    agent.execute_trade(
        signal="SELL",
        entry_price=100.0,
        quantity=10.0,
        stop_loss=105.0,
        take_profit=90.0
    )

    agent.update_market_price(95.0)

    assert agent.balance == 1000.0
    assert agent.get_equity() == 1050.0