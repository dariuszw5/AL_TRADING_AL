from src.agent.agent_engine import AgentEngine
from src.agent.risk_guard import RiskGuard


def test_agent_engine_has_risk_guard():
    engine = AgentEngine()

    assert hasattr(engine, "risk_guard")
    assert isinstance(engine.risk_guard, RiskGuard)


def test_agent_engine_risk_guard_allows_trade_initially():
    engine = AgentEngine()

    assert engine.risk_guard.can_trade() is True


def test_agent_engine_rejects_trade_when_risk_limit_reached():
    engine = AgentEngine()

    engine.risk_guard.record_loss(
        engine.risk_guard.max_daily_loss
    )

    result = engine.execute_trade(
        signal="BUY",
        entry_price=100.0,
        quantity=1.0,
        stop_loss=95.0,
        take_profit=110.0
    )

    assert result["status"] == "RISK_BLOCKED"


def test_agent_engine_risk_block_does_not_open_position():
    engine = AgentEngine()

    engine.risk_guard.record_loss(
        engine.risk_guard.max_daily_loss
    )

    engine.execute_trade(
        signal="BUY",
        entry_price=100.0,
        quantity=1.0,
        stop_loss=95.0,
        take_profit=110.0
    )

    assert engine.trading_engine.trade_manager.position is None