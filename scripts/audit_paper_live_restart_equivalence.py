import json
from pathlib import Path

from src.agent.agent_loop import AgentLoop
from src.data.candle import Candle


DATASETS = [
    Path("data/backtest/BTCUSDT_1m_forward_5000.json"),
    Path("data/backtest/BTCUSDT_1m_forward_5000_oos2.json"),
]

STATE_DIR = Path("data/live_state")


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


def make_provider(loop, candles, calls):
    def fake_get_candles(**kwargs):
        index = calls[-1]
        start = max(0, index - loop.config.limit)
        return candles[start:index]

    loop.data_provider.get_candles = fake_get_candles


def run_snapshot(loop, candles, index, calls):
    calls.append(index)
    return loop.run_live_once()


def get_trades(loop):
    return list(
        loop.agent.trading_engine.trade_manager.trade_history
    )


def run_continuous(candles):
    loop = AgentLoop()
    calls = []

    make_provider(loop, candles, calls)

    results = []

    for index in range(2, len(candles) + 1):
        results.append(
            run_snapshot(
                loop,
                candles,
                index,
                calls
            )
        )

    return {
        "results": results,
        "trades": get_trades(loop),
        "balance": loop.agent.balance,
        "peak_balance": loop.agent.peak_balance,
        "max_drawdown": loop.agent.max_drawdown,
        "last_timestamp": loop.last_processed_timestamp,
    }


def run_with_restart(candles, restart_index, state_path):
    first_loop = AgentLoop(
        state_file=state_path
    )

    first_calls = []

    make_provider(
        first_loop,
        candles,
        first_calls
    )

    first_results = []

    for index in range(2, restart_index + 1):
        first_results.append(
            run_snapshot(
                first_loop,
                candles,
                index,
                first_calls
            )
        )

    saved_timestamp = first_loop.last_processed_timestamp
    saved_trades = get_trades(first_loop)
    saved_balance = first_loop.agent.balance

    restarted_loop = AgentLoop(
        state_file=state_path
    )

    second_calls = []

    make_provider(
        restarted_loop,
        candles,
        second_calls
    )

    assert (
        restarted_loop.last_processed_timestamp
        == saved_timestamp
    )

    assert get_trades(restarted_loop) == saved_trades

    assert restarted_loop.agent.balance == saved_balance

    second_results = []

    for index in range(
        restart_index + 1,
        len(candles) + 1
    ):
        second_results.append(
            run_snapshot(
                restarted_loop,
                candles,
                index,
                second_calls
            )
        )

    return {
        "first_results": first_results,
        "second_results": second_results,
        "trades": get_trades(restarted_loop),
        "balance": restarted_loop.agent.balance,
        "peak_balance": restarted_loop.agent.peak_balance,
        "max_drawdown": restarted_loop.agent.max_drawdown,
        "last_timestamp": restarted_loop.last_processed_timestamp,
        "saved_timestamp": saved_timestamp,
    }


def processed_signals(results):
    return [
        result["signal"]
        for result in results
        if result["status"] == "PROCESSED"
    ]


def assert_results_match(continuous, restarted):
    continuous_signals = processed_signals(
        continuous["results"]
    )

    restarted_signals = processed_signals(
        restarted["first_results"]
        + restarted["second_results"]
    )

    assert continuous_signals == restarted_signals

    assert continuous["trades"] == restarted["trades"]

    assert continuous["balance"] == restarted["balance"]

    assert (
        continuous["peak_balance"]
        == restarted["peak_balance"]
    )

    assert (
        continuous["max_drawdown"]
        == restarted["max_drawdown"]
    )

    assert (
        continuous["last_timestamp"]
        == restarted["last_timestamp"]
    )


for dataset in DATASETS:
    state_path = (
        STATE_DIR
        / f"paper_live_restart_{dataset.stem}.json"
    )

    if state_path.exists():
        state_path.unlink()

    candles = load_candles(dataset)

    restart_index = len(candles) // 2

    continuous = run_continuous(candles)

    restarted = run_with_restart(
        candles,
        restart_index,
        state_path
    )

    assert_results_match(
        continuous,
        restarted
    )

    assert restarted["saved_timestamp"] is not None

    assert (
        restarted["last_timestamp"]
        == candles[-2].timestamp
    )

    if state_path.exists():
        state_path.unlink()

    print("=" * 100)
    print(
        f"PAPER-LIVE RESTART EQUIVALENCE | {dataset.name}"
    )
    print("=" * 100)

    print(
        f"restart index                 : {restart_index}"
    )

    print(
        f"saved timestamp               : "
        f"{restarted['saved_timestamp']}"
    )

    print(
        f"final timestamp               : "
        f"{restarted['last_timestamp']}"
    )

    print(
        f"continuous trades             : "
        f"{len(continuous['trades'])}"
    )

    print(
        f"restarted trades              : "
        f"{len(restarted['trades'])}"
    )

    print(
        f"continuous balance            : "
        f"{continuous['balance']}"
    )

    print(
        f"restarted balance             : "
        f"{restarted['balance']}"
    )

    print(
        "signals identical             : True"
    )

    print(
        "trades identical              : True"
    )

    print(
        "balance identical             : True"
    )

    print(
        "drawdown identical            : True"
    )

    print(
        "RESULT                        : PASS"
    )

    print()
