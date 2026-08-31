from src.agent.agent_loop import AgentLoop


def test_agent_loop_exists():
    loop = AgentLoop()

    assert loop is not None


def test_agent_loop_has_agent():
    loop = AgentLoop()

    assert loop.agent is not None


def test_agent_loop_has_data_provider():
    loop = AgentLoop()

    assert loop.data_provider is not None


def test_agent_loop_run_once():
    loop = AgentLoop()

    candles = [
        {
            "timestamp": 1,
            "open": 100.0,
            "high": 102.0,
            "low": 99.0,
            "close": 101.0,
            "volume": 10.0
        },
        {
            "timestamp": 2,
            "open": 101.0,
            "high": 104.0,
            "low": 100.0,
            "close": 103.0,
            "volume": 12.0
        },
        {
            "timestamp": 3,
            "open": 103.0,
            "high": 106.0,
            "low": 102.0,
            "close": 105.0,
            "volume": 15.0
        }
    ]

    result = loop.run_once(candles)

    assert result is not None
    assert "signal" in result


def test_agent_loop_run():
    loop = AgentLoop()

    candles = [
        {
            "timestamp": 1,
            "open": 100.0,
            "high": 102.0,
            "low": 99.0,
            "close": 101.0,
            "volume": 10.0
        },
        {
            "timestamp": 2,
            "open": 101.0,
            "high": 104.0,
            "low": 100.0,
            "close": 103.0,
            "volume": 12.0
        },
        {
            "timestamp": 3,
            "open": 103.0,
            "high": 106.0,
            "low": 102.0,
            "close": 105.0,
            "volume": 15.0
        }
    ]

    results = loop.run(
        candles=candles,
        iterations=3,
        interval=0
    )

    assert results is not None
    assert len(results) == 3