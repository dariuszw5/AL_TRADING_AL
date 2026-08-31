from src.agent.agent_engine import AgentEngine


def create_candle(timestamp, close):
    return {
        "timestamp": timestamp,
        "open": close - 1.0,
        "high": close + 1.0,
        "low": close - 2.0,
        "close": close,
        "volume": 10.0
    }


def test_agent_keeps_candle_history():
    engine = AgentEngine()

    candles = [
        create_candle(1, 100.0),
        create_candle(2, 101.0),
        create_candle(3, 102.0),
        create_candle(4, 103.0),
        create_candle(5, 104.0)
    ]

    for candle in candles:
        engine.run_cycle([candle])

    assert len(engine.data_manager.get_all()) == 5


def test_agent_history_contains_latest_candle():
    engine = AgentEngine()

    candle = create_candle(1, 100.0)

    engine.run_cycle([candle])

    latest = engine.data_manager.get_latest()

    assert latest is not None
    assert latest.close == 100.0