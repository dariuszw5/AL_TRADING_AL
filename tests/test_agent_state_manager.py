from src.agent.agent_state import AgentState


def test_agent_state_exists():
    state = AgentState()

    assert state is not None


def test_agent_state_initial_value():
    state = AgentState()

    assert state.get_state() == "IDLE"


def test_agent_state_can_change():
    state = AgentState()

    state.set_state("ANALYZING")

    assert state.get_state() == "ANALYZING"


def test_agent_state_can_be_stopped():
    state = AgentState()

    state.stop()

    assert state.get_state() == "STOPPED"


def test_agent_state_is_stopped():
    state = AgentState()

    assert state.is_stopped() is False

    state.stop()

    assert state.is_stopped() is True