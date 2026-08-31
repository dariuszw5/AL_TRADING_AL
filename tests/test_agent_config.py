from src.agent.agent_loop import AgentLoop
from src.agent.agent_config import AgentConfig


def test_agent_loop_has_config():
    loop = AgentLoop()

    assert loop.config is not None


def test_agent_loop_config_has_symbol():
    loop = AgentLoop()

    assert hasattr(loop.config, "symbol")
    assert loop.config.symbol == "BTCUSDT"


def test_agent_loop_config_has_interval():
    loop = AgentLoop()

    assert hasattr(loop.config, "interval")
    assert loop.config.interval == "1m"


def test_agent_loop_config_has_limit():
    loop = AgentLoop()

    assert hasattr(loop.config, "limit")
    assert loop.config.limit == 100


def test_agent_config_has_risk_percent():
    config = AgentConfig()

    assert hasattr(config, "risk_percent")
    assert config.risk_percent == 5.0


def test_agent_config_has_risk_reward_ratio():
    config = AgentConfig()

    assert hasattr(config, "risk_reward_ratio")
    assert config.risk_reward_ratio == 2.0


def test_agent_config_has_initial_balance():
    config = AgentConfig()

    assert hasattr(config, "initial_balance")
    assert config.initial_balance == 1000.0