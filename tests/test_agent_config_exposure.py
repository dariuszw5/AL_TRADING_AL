from src.agent.agent_config import AgentConfig


def test_agent_config_has_max_exposure_percent():
    config = AgentConfig()

    assert config.max_exposure_percent == 100.0


def test_agent_config_custom_max_exposure_percent():
    config = AgentConfig(
        max_exposure_percent=150.0
    )

    assert config.max_exposure_percent == 150.0
