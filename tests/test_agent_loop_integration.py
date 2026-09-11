from src.agent.agent_loop import AgentLoop
from src.data.candle import Candle


def make_candles(count=100):
    candles = []

    prices = [
        100.0,
        100.2,
        99.9,
        100.1,
        100.0,
        99.8,
        100.1,
        100.3,
        100.0,
        99.9,
    ]

    for index in range(count):
        close = prices[index % len(prices)]

        candles.append(
            Candle(
                timestamp=index + 1,
                open=close,
                high=close + 0.2,
                low=close - 0.2,
                close=close,
                volume=10.0
            )
        )

    return candles


def test_agent_loop_live_integrates_with_real_agent_engine(monkeypatch):
    loop = AgentLoop()

    candles = make_candles()

    monkeypatch.setattr(
        loop.data_provider,
        "get_candles",
        lambda **kwargs: candles
    )

    result = loop.run_live_once()

    assert result["status"] == "PROCESSED"
    assert result["timestamp"] == 99
    assert result["signal"] in ("BUY", "SELL", "HOLD")
    assert "result" in result
    assert loop.last_processed_timestamp == 99
    assert len(loop.history) == len(candles) - 1
