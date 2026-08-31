from src.agent.agent_engine import AgentEngine


def test_agent_engine_has_state():
    engine = AgentEngine()

    assert hasattr(engine, "state")


def test_agent_engine_initial_state():
    engine = AgentEngine()

    assert engine.state == "IDLE"


def test_agent_engine_state_can_be_changed():
    engine = AgentEngine()

    engine.state = "ANALYZING"

    assert engine.state == "ANALYZING"


def test_agent_engine_has_stop_method():
    engine = AgentEngine()

    assert hasattr(engine, "stop")


def test_agent_engine_stop():
    engine = AgentEngine()

    engine.stop()

    assert engine.state == "STOPPED"
    