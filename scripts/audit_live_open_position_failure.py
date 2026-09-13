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
    print("LIVE API FAILURE WITH OPEN POSITION AUDIT")
    print("=" * 100)

    loop = AgentLoop(config=AgentConfig())

    # Najpierw tworzymy deterministyczną pozycję testową.
    position = {
        "side": "LONG",
        "entry_price": 100.0,
        "quantity": 1.0,
        "stop_loss": 95.0,
        "take_profit": 110.0,
        "entry_timestamp": 1000,
    }

    loop.agent.trading_engine.trade_manager.position = position.copy()

    snapshots = [
        [
            candle(1000, 100.0),
            candle(2000, 101.0),
        ],
        None,
        None,
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

    current = {"index": 0}

    def provider(**kwargs):
        snapshot = snapshots[current["index"]]

        if snapshot is None:
            raise RuntimeError("SIMULATED_API_FAILURE_WITH_POSITION")

        return snapshot

    loop.data_provider.get_candles = provider

    # 1. Stan początkowy.
    original_position = (
        loop.agent.trading_engine.trade_manager.position.copy()
    )

    assert original_position["side"] == "LONG"

    print("OPEN POSITION CREATED    : PASS")

    # 2. Pierwsze normalne przetworzenie.
    result = loop.run_live_once()

    assert result["status"] == "PROCESSED"

    current_position = (
        loop.agent.trading_engine.trade_manager.position
    )

    assert current_position == original_position

    print("POSITION PRESERVED       : PASS")

    # 3. API failure.
    current["index"] = 1

    result = loop.run_live_once()

    assert result["status"] == "API_ERROR"
    assert result["signal"] == "HOLD"
    assert result["result"] is None

    current_position = (
        loop.agent.trading_engine.trade_manager.position
    )

    assert current_position == original_position
    assert loop.last_processed_timestamp == 1000

    print("API FAILURE              : PASS")
    print("POSITION UNCHANGED       : PASS")
    print("TIMESTAMP UNCHANGED      : PASS")

    # 4. Kolejna awaria.
    current["index"] = 2

    result = loop.run_live_once()

    assert result["status"] == "API_ERROR"

    current_position = (
        loop.agent.trading_engine.trade_manager.position
    )

    assert current_position == original_position

    print("REPEATED FAILURE         : PASS")
    print("POSITION STILL UNCHANGED : PASS")

    # 5. Recovery.
    current["index"] = 3

    result = loop.run_live_once()

    assert result["status"] == "PROCESSED"
    assert result["timestamp"] == 2000

    current_position = (
        loop.agent.trading_engine.trade_manager.position
    )

    assert current_position == original_position

    print("API RECOVERY             : PASS")
    print("POSITION AFTER RECOVERY  : PASS")

    # 6. Kolejna normalna świeca.
    current["index"] = 4

    result = loop.run_live_once()

    assert result["status"] == "PROCESSED"
    assert result["timestamp"] == 3000

    current_position = (
        loop.agent.trading_engine.trade_manager.position
    )

    assert current_position == original_position

    print("POST-RECOVERY PROCESSING : PASS")
    print("POSITION STILL VALID     : PASS")

    print()
    print("=" * 100)
    print("RESULT: PASS")
    print("=" * 100)


if __name__ == "__main__":
    main()
