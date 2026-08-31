from src.agent.agent_engine import AgentEngine


def test_agent_records_loss_after_closed_trade():
    engine = AgentEngine()

    engine.execute_trade(
        signal="BUY",
        entry_price=100.0,
        quantity=1.0,
        stop_loss=95.0,
        take_profit=110.0
    )

    engine.trading_engine.check_position(95.0)

    assert engine.risk_guard.daily_loss > 0.0


def test_agent_does_not_record_loss_for_profitable_trade():
    engine = AgentEngine()

    engine.execute_trade(
        signal="BUY",
        entry_price=100.0,
        quantity=1.0,
        stop_loss=95.0,
        take_profit=110.0
    )

    engine.trading_engine.check_position(110.0)

    assert engine.risk_guard.daily_loss == 0.0


def test_agent_risk_limit_can_block_after_losses():
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