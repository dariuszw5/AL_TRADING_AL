import json
from pathlib import Path

from src.agent.agent_loop import AgentLoop
from src.data.candle import Candle


DATASETS = [
    Path("data/backtest/BTCUSDT_1m_forward_5000.json"),
    Path("data/backtest/BTCUSDT_1m_forward_5000_oos2.json"),
]


def load_candles(path):
    data = json.loads(path.read_text(encoding="utf-8"))

    return [
        Candle(
            timestamp=item["timestamp"],
            open=float(item["open"]),
            high=float(item["high"]),
            low=float(item["low"]),
            close=float(item["close"]),
            volume=float(item["volume"]),
        )
        for item in data
    ]


def replay(path):
    candles = load_candles(path)
    loop = AgentLoop()

    calls = []
    original_get_candles = loop.data_provider.get_candles

    def fake_get_candles(**kwargs):
        index = calls[-1] if calls else 1
        start = max(0, index - loop.config.limit)
        return candles[start:index]

    def set_index(index):
        calls.append(index)

    loop.data_provider.get_candles = fake_get_candles

    processed = 0
    waiting = 0
    no_new = 0
    signals = {"BUY": 0, "SELL": 0, "HOLD": 0}

    for index in range(2, len(candles) + 1):
        set_index(index)

        result = loop.run_live_once()

        if result["status"] == "PROCESSED":
            processed += 1
            signals[result["signal"]] += 1
        elif result["status"] == "WAITING_FOR_CANDLE":
            waiting += 1
        elif result["status"] == "NO_NEW_CANDLE":
            no_new += 1
        else:
            raise AssertionError(
                f"Unexpected status: {result['status']}"
            )

    last_timestamp = candles[-2].timestamp

    assert processed == len(candles) - 1
    assert waiting == 0
    assert no_new == 0
    assert loop.last_processed_timestamp == last_timestamp
    assert len(loop.history) == loop.config.limit
    assert loop.history[-1].timestamp == last_timestamp

    # Same API snapshot again must not process the same closed candle twice.
    calls.append(len(candles))
    duplicate = loop.run_live_once()

    assert duplicate["status"] == "NO_NEW_CANDLE"
    assert duplicate["timestamp"] == last_timestamp

    return {
        "candles": len(candles),
        "processed": processed,
        "waiting": waiting,
        "no_new": no_new,
        "buy": signals["BUY"],
        "sell": signals["SELL"],
        "hold": signals["HOLD"],
        "last_timestamp": loop.last_processed_timestamp,
        "history": len(loop.history),
        "duplicate_status": duplicate["status"],
    }


for dataset in DATASETS:
    result = replay(dataset)

    print("=" * 90)
    print(f"LIVE REPLAY | {dataset}")
    print("=" * 90)
    for key, value in result.items():
        print(f"{key:20} = {value}")
    print()
