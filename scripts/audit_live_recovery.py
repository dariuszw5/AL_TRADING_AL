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


def main():
    print("=" * 100)
    print("LIVE API FAILURE -> RECOVERY AUDIT")
    print("=" * 100)

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
        None,
        None,
        [
            candle(1000, 100.0),
            candle(2000, 101.0),
            candle(3000, 102.0),
            candle(4000, 103.0),
        ],
        [
            candle(1000, 100.0),
            candle(2000, 101.0),
            candle(3000, 102.0),
            candle(4000, 103.0),
            candle(5000, 104.0),
        ],
    ]

    current = {"index": 0}

    def provider(**kwargs):
        snapshot = snapshots[current["index"]]

        if snapshot is None:
            raise RuntimeError("SIMULATED_API_FAILURE")

        return snapshot

    loop.data_provider.get_candles = provider

    # 1. Normal processing.
    result = loop.run_live_once()

    assert result["status"] == "PROCESSED"
    assert result["timestamp"] == 1000
    assert loop.last_processed_timestamp == 1000

    print("INITIAL PROCESSING       : PASS")

    # 2. Normal progression.
    current["index"] = 1

    result = loop.run_live_once()

    assert result["status"] == "PROCESSED"
    assert result["timestamp"] == 2000
    assert loop.last_processed_timestamp == 2000

    print("PRE-FAILURE PROGRESSION  : PASS")

    # 3. API failure.
    current["index"] = 2

    result = loop.run_live_once()

    assert result["status"] == "API_ERROR"
    assert result["signal"] == "HOLD"
    assert result["result"] is None

    # Critical: API failure must NOT advance the timestamp.
    assert loop.last_processed_timestamp == 2000

    print("API FAILURE              : PASS")
    print("STATE PRESERVED          : PASS")

    # 4. Another failed request.
    current["index"] = 3

    result = loop.run_live_once()

    assert result["status"] == "API_ERROR"
    assert loop.last_processed_timestamp == 2000

    print("REPEATED FAILURE         : PASS")

    # 5. API recovers.
    current["index"] = 4

    result = loop.run_live_once()

    assert result["status"] == "PROCESSED"
    assert result["timestamp"] == 3000
    assert loop.last_processed_timestamp == 3000

    print("API RECOVERY             : PASS")

    # 6. Continue normally after recovery.
    current["index"] = 5

    result = loop.run_live_once()

    assert result["status"] == "PROCESSED"
    assert result["timestamp"] == 4000
    assert loop.last_processed_timestamp == 4000

    print("POST-RECOVERY PROCESSING : PASS")

    # 7. Verify no duplicate timestamps in history.
    timestamps = [item.timestamp for item in loop.history]

    assert timestamps == sorted(set(timestamps))
    assert timestamps == [1000, 2000, 3000, 4000]

    print("NO DUPLICATE HISTORY     : PASS")

    # 8. Final state.
    assert loop.last_processed_timestamp == 4000
    assert len(loop.history) == 4

    print("FINAL STATE              : PASS")

    print()
    print("=" * 100)
    print("RESULT: PASS")
    print("=" * 100)


if __name__ == "__main__":
    main()
