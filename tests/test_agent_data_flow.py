from src.agent.agent_engine import AgentEngine
from src.data.candle import Candle


def test_agent_data_flow():
    engine = AgentEngine()

    candles = engine.data_provider.get_candles(
        symbol="BTCUSDT",
        interval="1m",
        limit=20
    )

    assert isinstance(candles, list)
    assert len(candles) == 20
    assert all(isinstance(candle, Candle) for candle in candles)


def test_agent_can_analyze_provider_data():
    engine = AgentEngine()

    candles = engine.data_provider.get_candles(
        symbol="BTCUSDT",
        interval="1m",
        limit=20
    )

    result = engine.analyze(candles)

    assert result is not None
    assert "signal" in result
    assert result["signal"] in ("BUY", "SELL", "HOLD")
    