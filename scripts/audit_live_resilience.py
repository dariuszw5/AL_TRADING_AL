from src.agent.agent_config import AgentConfig
from src.agent.agent_loop import AgentLoop
from src.data.candle import Candle


def candle(timestamp, close):
    return Candle(
        timestamp=timestamp,
        open=close,
        high=close + 1.0,
        low=close - 1.0,
        close=close,
        volume=1.0,
    )


def section(title):
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


def test_empty_response():
    loop = AgentLoop(config=AgentConfig())

    loop.data_provider.get_candles = lambda **kwargs: []

    result = loop.run_live_once()

    assert result["status"] == "WAITING_FOR_CANDLE"
    assert result["signal"] == "HOLD"
    assert result["result"] is None

    print("EMPTY API RESPONSE       : PASS")


def test_single_candle():
    loop = AgentLoop(config=AgentConfig())

    candles = [
        candle(1000, 100.0),
    ]

    loop.data_provider.get_candles = lambda **kwargs: candles

    result = loop.run_live_once()

    assert result["status"] == "WAITING_FOR_CANDLE"
    assert result["signal"] == "HOLD"
    assert result["result"] is None

    print("ONE CANDLE RESPONSE      : PASS")


def test_duplicate_candle():
    loop = AgentLoop(config=AgentConfig())

    candles = [
        candle(1000, 100.0),
        candle(2000, 101.0),
    ]

    snapshots = [
        candles,
        candles,
    ]

    current = {"value": 0}

    def provider(**kwargs):
        return snapshots[current["value"]]

    loop.data_provider.get_candles = provider

    first = loop.run_live_once()

    assert first["status"] == "PROCESSED"
    assert first["timestamp"] == 1000

    current["value"] = 1

    second = loop.run_live_once()

    assert second["status"] == "NO_NEW_CANDLE"
    assert second["timestamp"] == 1000

    print("DUPLICATE CANDLE         : PASS")


def test_progression():
    loop = AgentLoop(config=AgentConfig())

    snapshots = [
        [
            candle(1000, 100.0),
            candle(2000, 101.0),
        ],
        [
            candle(1000, 100.0),
            candle(2000, 101.0),
            candle(3000, 102.0),
        ],
        [
            candle(1000, 100.0),
            candle(2000, 101.0),
            candle(3000, 102.0),
            candle(4000, 103.0),
        ],
    ]

    current = {"value": 0}

    def provider(**kwargs):
        return snapshots[current["value"]]

    loop.data_provider.get_candles = provider

    results = []

    for index in range(len(snapshots)):
        current["value"] = index
        results.append(loop.run_live_once())

    assert [r["status"] for r in results] == [
        "PROCESSED",
        "PROCESSED",
        "PROCESSED",
    ]

    assert [r["timestamp"] for r in results] == [
        1000,
        2000,
        3000,
    ]

    assert loop.last_processed_timestamp == 3000
    assert [c.timestamp for c in loop.history] == [
        1000,
        2000,
        3000,
    ]

    print("SEQUENTIAL PROGRESSION  : PASS")


def test_restart_flat():
    config = AgentConfig()

    first_loop = AgentLoop(config=config)

    candles = [
        candle(1000, 100.0),
        candle(2000, 101.0),
    ]

    first_loop.data_provider.get_candles = lambda **kwargs: candles

    first = first_loop.run_live_once()

    assert first["status"] == "PROCESSED"
    assert first_loop.last_processed_timestamp == 1000

    second_loop = AgentLoop(config=config)

    second_loop.data_provider.get_candles = lambda **kwargs: candles

    second = second_loop.run_live_once()

    assert second["status"] == "PROCESSED"
    assert second["timestamp"] == 1000
    assert second_loop.last_processed_timestamp == 1000

    print("PROCESS RESTART (FLAT)  : PASS")


def test_provider_exception():
    loop = AgentLoop(config=AgentConfig())

    def failing_provider(**kwargs):
        raise RuntimeError("SIMULATED_API_FAILURE")

    loop.data_provider.get_candles = failing_provider

    result = loop.run_live_once()

    assert result["status"] == "API_ERROR"
    assert result["signal"] == "HOLD"
    assert result["result"] is None
    assert result["error"] == "SIMULATED_API_FAILURE"

    print("API EXCEPTION BEHAVIOR   : HANDLED")
    print("  Provider exceptions are converted to API_ERROR/HOLD.")


def main():
    section("LIVE EXECUTION RESILIENCE AUDIT")

    test_empty_response()
    test_single_candle()
    test_duplicate_candle()
    test_progression()
    test_restart_flat()
    test_provider_exception()

    section("AUDIT RESULT")

    print("Basic live-state protections : PASS")
    print("Provider exception handling  : PASS")
    print()
    print("Provider exceptions are safely converted to API_ERROR/HOLD.")


if __name__ == "__main__":
    main()


