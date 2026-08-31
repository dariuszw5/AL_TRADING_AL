from src.agent.agent_engine import AgentEngine
from src.agent.agent_config import AgentConfig


def test_agent_can_open_second_trade_after_first_is_closed():
    agent = AgentEngine(
        config=AgentConfig(
            initial_balance=1000.0,
            risk_percent=10.0
        )
    )

    first = agent.execute_trade(
        signal="BUY",
        entry_price=100.0,
        quantity=10.0,
        stop_loss=95.0,
        take_profit=110.0
    )

    assert first["side"] == "BUY"

    first_result = agent.trading_engine.check_position(95.0)

    assert first_result is not None
    assert first_result["profit"] == -50.0
    assert agent.balance == 950.0

    second = agent.execute_trade(
        signal="SELL",
        entry_price=100.0,
        quantity=10.0,
        stop_loss=105.0,
        take_profit=90.0
    )

    assert second["side"] == "SELL"


def test_agent_can_close_sell_trade():
    agent = AgentEngine(
        config=AgentConfig(
            initial_balance=1000.0,
            risk_percent=10.0
        )
    )

    agent.execute_trade(
        signal="SELL",
        entry_price=100.0,
        quantity=10.0,
        stop_loss=105.0,
        take_profit=90.0
    )

    result = agent.trading_engine.check_position(90.0)

    assert result is not None
    assert result["profit"] == 100.0
    assert agent.balance == 1100.0


def test_agent_multiple_trades_update_equity_curve():
    agent = AgentEngine(
        config=AgentConfig(
            initial_balance=1000.0,
            risk_percent=10.0
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

    agent.execute_trade(
        signal="SELL",
        entry_price=100.0,
        quantity=10.0,
        stop_loss=105.0,
        take_profit=90.0
    )

    agent.trading_engine.check_position(90.0)

    assert agent.balance == 1200.0
    assert agent.get_peak_balance() == 1200.0
    assert agent.get_max_drawdown() == 0.0