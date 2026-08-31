from src.agent.agent_engine import AgentEngine


def test_agent_engine_has_decision_engine():
    engine = AgentEngine()

    assert hasattr(engine, "decision_engine")


def test_agent_engine_uses_decision_engine():
    engine = AgentEngine()

    analysis = {
        "sma": [100.0],
        "ema": [105.0],
        "rsi": [25.0]
    }

    result = engine.decision_engine.decide(analysis)

    assert result == "BUY"