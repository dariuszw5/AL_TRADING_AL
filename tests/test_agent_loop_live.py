from src.agent.agent_loop import AgentLoop
from src.data.candle import Candle


def make_candle(timestamp, close=100.0):
    return Candle(
        timestamp=timestamp,
        open=close,
        high=close + 1.0,
        low=close - 1.0,
        close=close,
        volume=10.0
    )


def test_agent_loop_passes_config_to_agent():
    loop = AgentLoop()

    assert loop.agent.config is loop.config


def test_agent_loop_initializes_live_state():
    loop = AgentLoop()

    assert loop.history == []
    assert loop.last_processed_timestamp is None


def test_agent_loop_update_history_keeps_chronological_candles():
    loop = AgentLoop()

    candles = [
        make_candle(1, 100.0),
        make_candle(2, 101.0),
        make_candle(3, 102.0),
    ]

    history = loop._update_history(candles)

    assert [c.timestamp for c in history] == [1, 2, 3]


def test_agent_loop_update_history_ignores_duplicates():
    loop = AgentLoop()

    loop._update_history([
        make_candle(1),
        make_candle(2),
    ])

    loop._update_history([
        make_candle(2),
        make_candle(3),
    ])

    assert [c.timestamp for c in loop.history] == [1, 2, 3]


def test_agent_loop_update_history_respects_limit():
    loop = AgentLoop()

    loop.config.limit = 3

    loop._update_history([
        make_candle(1),
        make_candle(2),
        make_candle(3),
        make_candle(4),
        make_candle(5),
    ])

    assert [c.timestamp for c in loop.history] == [3, 4, 5]


def test_agent_loop_run_live_once_processes_closed_candle(monkeypatch):
    loop = AgentLoop()

    candles = [
        make_candle(1, 100.0),
        make_candle(2, 101.0),
        make_candle(3, 102.0),
    ]

    monkeypatch.setattr(
        loop.data_provider,
        "get_candles",
        lambda **kwargs: candles
    )

    monkeypatch.setattr(
        loop.agent,
        "run_cycle",
        lambda history: {
            "signal": "HOLD",
            "position": None,
            "result": None
        }
    )

    result = loop.run_live_once()

    assert result["status"] == "PROCESSED"
    assert result["timestamp"] == 2
    assert result["signal"] == "HOLD"
    assert loop.last_processed_timestamp == 2


def test_agent_loop_run_live_once_ignores_same_candle(monkeypatch):
    loop = AgentLoop()

    candles = [
        make_candle(1, 100.0),
        make_candle(2, 101.0),
        make_candle(3, 102.0),
    ]

    monkeypatch.setattr(
        loop.data_provider,
        "get_candles",
        lambda **kwargs: candles
    )

    calls = []

    monkeypatch.setattr(
        loop.agent,
        "run_cycle",
        lambda history: calls.append(history) or {
            "signal": "HOLD",
            "position": None,
            "result": None
        }
    )

    first = loop.run_live_once()
    second = loop.run_live_once()

    assert first["status"] == "PROCESSED"
    assert second["status"] == "NO_NEW_CANDLE"
    assert len(calls) == 1


def test_agent_loop_run_live_once_waits_for_enough_candles(monkeypatch):
    loop = AgentLoop()

    monkeypatch.setattr(
        loop.data_provider,
        "get_candles",
        lambda **kwargs: [make_candle(1)]
    )

    result = loop.run_live_once()

    assert result["status"] == "WAITING_FOR_CANDLE"
