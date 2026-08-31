from src.agent.agent_engine import AgentEngine


def test_agent_engine_processes_multiple_cycles():
    engine = AgentEngine()

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

    results = []

    for candle in candles:
        results.append(engine.run_cycle([candle]))

    assert len(results) == 3
    assert all(result is not None for result in results)


def test_agent_engine_has_run():
    engine = AgentEngine()

    assert hasattr(engine, "run")


def test_agent_engine_run_returns_results():
    engine = AgentEngine()

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

    results = engine.run(candles)

    assert isinstance(results, list)
    assert len(results) == 3