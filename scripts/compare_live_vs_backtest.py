import json
from pathlib import Path

from src.agent.agent_config import AgentConfig
from src.agent.agent_engine import AgentEngine
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


def trade_signature(trade):
    return (
        trade.get("signal"),
        trade.get("entry_timestamp"),
        trade.get("entry_price"),
        trade.get("exit_timestamp"),
        trade.get("exit_price"),
        trade.get("exit_reason"),
    )


def run_backtest(candles):
    engine = AgentEngine(config=AgentConfig())

    results = engine.run(candles[:-1])

    signals = [
        result.get("signal")
        for result in results[:len(candles) - 1]
    ]

    trades = [
        trade_signature(trade)
        for trade in engine.trade_history.get_trades()
    ]

    return signals, trades, engine


def run_live_replay(candles):
    loop = AgentLoop(config=AgentConfig())

    index = {"value": 0}

    def fake_get_candles(**kwargs):
        end = index["value"]
        start = max(0, end - loop.config.limit)

        return candles[start:end]

    loop.data_provider.get_candles = fake_get_candles

    signals = []

    for end in range(2, len(candles) + 1):
        index["value"] = end

        result = loop.run_live_once()

        assert result["status"] == "PROCESSED"
        signals.append(result["signal"])

    trades = [
        trade_signature(trade)
        for trade in loop.agent.trade_history.get_trades()
    ]

    return signals, trades, loop


def compare(name, candles):
    backtest_signals, backtest_trades, backtest_engine = run_backtest(candles)
    live_signals, live_trades, live_loop = run_live_replay(candles)

    print("=" * 100)
    print(f"LIVE vs BACKTEST | {name}")
    print("=" * 100)

    print(f"Closed candles compared : {len(candles) - 1}")
    print(f"Backtest signals        : {len(backtest_signals)}")
    print(f"Live signals            : {len(live_signals)}")
    print(f"Signals identical       : {backtest_signals == live_signals}")

    print()
    print(f"Backtest trades         : {len(backtest_trades)}")
    print(f"Live trades             : {len(live_trades)}")
    print(f"Trades identical        : {backtest_trades == live_trades}")

    signal_differences = []

    for index, (backtest, live) in enumerate(
        zip(backtest_signals, live_signals),
        start=1
    ):
        if backtest != live:
            signal_differences.append(
                (index, backtest, live)
            )

    if signal_differences:
        print()
        print("FIRST SIGNAL DIFFERENCES")
        for item in signal_differences[:10]:
            print(
                f"index={item[0]} | "
                f"backtest={item[1]} | "
                f"live={item[2]}"
            )

    if backtest_trades != live_trades:
        print()
        print("TRADE DIFFERENCES")

        max_len = max(
            len(backtest_trades),
            len(live_trades)
        )

        for index in range(max_len):
            backtest_trade = (
                backtest_trades[index]
                if index < len(backtest_trades)
                else None
            )
            live_trade = (
                live_trades[index]
                if index < len(live_trades)
                else None
            )

            if backtest_trade != live_trade:
                print(f"trade #{index + 1}")
                print(f"  BACKTEST: {backtest_trade}")
                print(f"  LIVE:     {live_trade}")

    assert backtest_signals == live_signals
    assert backtest_trades == live_trades

    print()
    print("RESULT: PASS")
    print()


for dataset in DATASETS:
    compare(dataset.name, load_candles(dataset))
