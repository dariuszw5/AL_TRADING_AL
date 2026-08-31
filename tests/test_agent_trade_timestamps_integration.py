from src.agent.agent_engine import AgentEngine
from src.agent.agent_config import AgentConfig


def test_agent_passes_entry_timestamp_to_trade():
    agent = AgentEngine(
        config=AgentConfig(
            initial_balance=1000.0
        )
    )

    agent.analyze = lambda candles: {"signal": "BUY"}

    result = agent.run_cycle([
        {
            "timestamp": 123456,
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 100.0,
            "volume": 10.0
        }
    ])

    assert result["position"] is not None
    assert result["position"]["side"] == "BUY"
    assert result["position"]["entry_timestamp"] == 123456


def test_agent_passes_entry_and_exit_timestamp_to_trade():
    agent = AgentEngine(
        config=AgentConfig(
            initial_balance=1000.0
        )
    )

    agent.analyze = lambda candles: {"signal": "BUY"}

    first = agent.run_cycle([
        {
            "timestamp": 123456,
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 100.0,
            "volume": 10.0
        }
    ])

    assert first["position"] is not None

    agent.analyze = lambda candles: {"signal": "HOLD"}

    second = agent.run_cycle([
        {
            "timestamp": 123516,
            "open": 109.0,
            "high": 111.0,
            "low": 108.0,
            "close": 110.0,
            "volume": 10.0
        }
    ])

    assert second["result"] is not None
    assert second["result"]["side"] == "BUY"
    assert second["result"]["entry_timestamp"] == 123456
    assert second["result"]["exit_timestamp"] == 123516