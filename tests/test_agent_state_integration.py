from src.agent.agent_engine import AgentEngine
from src.agent.agent_state import AgentState


def test_agent_engine_has_agent_state():
    engine = AgentEngine()

    assert hasattr(engine, "agent_state")
    assert isinstance(engine.agent_state, AgentState)


def test_agent_engine_initial_state():
    engine = AgentEngine()

    assert engine.agent_state.get_state() == "IDLE"


def test_agent_engine_stop_uses_agent_state():
    engine = AgentEngine()

    engine.stop()

    assert engine.agent_state.is_stopped() is True


def test_agent_engine_state_property():
    engine = AgentEngine()

    assert engine.state == "IDLE"

    engine.agent_state.set_state("ANALYZING")

    assert engine.state == "ANALYZING"