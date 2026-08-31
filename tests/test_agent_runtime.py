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


def test_agent_runtime_processes_multiple_candles():
    engine = AgentEngine()

    candles = [
        create_candle(1, 100.0),
        create_candle(2, 101.0),
        create_candle(3, 102.0),
        create_candle(4, 103.0),
        create_candle(5, 104.0),
        create_candle(6, 105.0),
        create_candle(7, 106.0),
        create_candle(8, 107.0),
        create_candle(9, 108.0),
        create_candle(10, 109.0),
        create_candle(11, 110.0),
        create_candle(12, 111.0),
        create_candle(13, 112.0),
        create_candle(14, 113.0),
        create_candle(15, 114.0),
        create_candle(16, 115.0),
        create_candle(17, 116.0),
        create_candle(18, 117.0),
        create_candle(19, 118.0),
        create_candle(20, 119.0)
    ]

    results = []

    for candle in candles:
        result = engine.run_cycle([candle])
        results.append(result)

    assert len(results) == 20
    assert len(engine.data_manager.get_all()) == 20


def test_agent_runtime_returns_signal():
    engine = AgentEngine()

    candle = create_candle(1, 100.0)

    result = engine.run_cycle([candle])

    assert "signal" in result
    assert result["signal"] in ("BUY", "SELL", "HOLD")
    