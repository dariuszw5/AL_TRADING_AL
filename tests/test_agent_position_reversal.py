from src.agent.agent_engine import AgentEngine


def test_agent_does_not_reverse_buy_to_sell_on_opposite_signal():
    agent = AgentEngine()

    agent.analyze = lambda candles: {"signal": "BUY"}

    first = agent.run_cycle([
        {
            "timestamp": 1,
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 100.0,
            "volume": 10.0
        }
    ])

    assert first["position"] is not None
    assert first["position"]["side"] == "BUY"

    agent.analyze = lambda candles: {"signal": "SELL"}

    second = agent.run_cycle([
        {
            "timestamp": 2,
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 100.0,
            "volume": 10.0
        }
    ])

    assert second["result"] is None
    assert second["position"] is not None
    assert second["position"]["side"] == "BUY"


def test_agent_does_not_reverse_sell_to_buy_on_opposite_signal():
    agent = AgentEngine()

    agent.analyze = lambda candles: {"signal": "SELL"}

    first = agent.run_cycle([
        {
            "timestamp": 1,
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 100.0,
            "volume": 10.0
        }
    ])

    assert first["position"] is not None
    assert first["position"]["side"] == "SELL"

    agent.analyze = lambda candles: {"signal": "BUY"}

    second = agent.run_cycle([
        {
            "timestamp": 2,
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 100.0,
            "volume": 10.0
        }
    ])

    assert second["result"] is None
    assert second["position"] is not None
    assert second["position"]["side"] == "SELL"
