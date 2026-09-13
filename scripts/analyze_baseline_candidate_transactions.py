from src.backtest.backtest_runner import BacktestRunner


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALIDATION": "data/backtest/BTCUSDT_1m_validation_5000.json",
    "TEST": "data/backtest/BTCUSDT_1m_test_5000.json",
}


STRATEGIES = {
    "BASELINE": {
        "buy": 30.00,
        "sell": 70.00,
    },
    "CANDIDATE": {
        "buy": 35.50,
        "sell": 68.50,
    },
}


MIN_DIFFERENCE = 1.0
TRADING_FEE = 0.0004
RSI_METHOD = "classic"


def run_backtest(data_file, buy_rsi, sell_rsi):

    runner = BacktestRunner(
        symbol="BTCUSDT",
        interval="1m",
        limit=5000,
        initial_balance=1000.0,
        buy_rsi=buy_rsi,
        sell_rsi=sell_rsi,
        min_difference=MIN_DIFFERENCE,
        trading_fee=TRADING_FEE,
        rsi_method=RSI_METHOD,
        data_source="file",
        data_file=data_file,
    )

    runner.load_data()
    runner.run()

    return runner


def find_candle_index(candles, timestamp):

    for index, candle in enumerate(candles):

        if candle.timestamp == timestamp:
            return index

    return None


def trade_info(trade, candles):

    entry_timestamp = trade.get("entry_timestamp")
    exit_timestamp = trade.get("exit_timestamp")

    entry_index = find_candle_index(
        candles,
        entry_timestamp
    )

    exit_index = find_candle_index(
        candles,
        exit_timestamp
    )

    side = trade.get(
        "side",
        trade.get("signal", "?")
    )

    profit = float(
        trade.get("profit", 0.0)
    )

    return {
        "entry": entry_index,
        "exit": exit_index,
        "side": side,
        "profit": profit,
        "entry_timestamp": entry_timestamp,
        "exit_timestamp": exit_timestamp,
    }


def build_map(trades, candles):

    result = {}

    for trade in trades:

        info = trade_info(
            trade,
            candles
        )

        if info["entry"] is not None:

            result[info["entry"]] = info

    return result


def print_trade(label, info):

    if info is None:

        print(
            f"{label}: NONE"
        )

        return

    print(
        f"{label}: "
        f"{info['side']:>4} "
        f"{info['entry']:>5} -> "
        f"{info['exit']:>5} | "
        f"P/L={info['profit']:+.4f}"
    )


def analyze_dataset(name, path):

    baseline_runner = run_backtest(
        path,
        STRATEGIES["BASELINE"]["buy"],
        STRATEGIES["BASELINE"]["sell"],
    )

    candidate_runner = run_backtest(
        path,
        STRATEGIES["CANDIDATE"]["buy"],
        STRATEGIES["CANDIDATE"]["sell"],
    )

    candles = baseline_runner.candles

    baseline_map = build_map(
        baseline_runner.get_trades(),
        candles
    )

    candidate_map = build_map(
        candidate_runner.get_trades(),
        candles
    )

    baseline_entries = set(
        baseline_map
    )

    candidate_entries = set(
        candidate_map
    )

    common_entries = sorted(
        baseline_entries &
        candidate_entries
    )

    baseline_only = sorted(
        baseline_entries -
        candidate_entries
    )

    candidate_only = sorted(
        candidate_entries -
        baseline_entries
    )

    baseline_only_profit = sum(
        baseline_map[index]["profit"]
        for index in baseline_only
    )

    candidate_only_profit = sum(
        candidate_map[index]["profit"]
        for index in candidate_only
    )

    common_baseline_profit = sum(
        baseline_map[index]["profit"]
        for index in common_entries
    )

    common_candidate_profit = sum(
        candidate_map[index]["profit"]
        for index in common_entries
    )

    actual_total_delta = (
        candidate_runner.get_total_profit()
        - baseline_runner.get_total_profit()
    )

    print()
    print("=" * 135)
    print(
        f"{name} | UNIQUE TRANSACTION ANALYSIS | "
        f"FEE={TRADING_FEE:.4f}"
    )
    print("=" * 135)

    print()
    print(
        f"BASELINE  30/70       | "
        f"TRADES={len(baseline_map):2d} | "
        f"PROFIT={baseline_runner.get_total_profit():+.4f}"
    )

    print(
        f"CANDIDATE 35.50/68.50 | "
        f"TRADES={len(candidate_map):2d} | "
        f"PROFIT={candidate_runner.get_total_profit():+.4f}"
    )

    print(
        f"ACTUAL PROFIT DELTA   | "
        f"{actual_total_delta:+.4f}"
    )

    print()
    print(
        f"COMMON ENTRIES: "
        f"{len(common_entries)}"
    )

    print(
        f"BASELINE ONLY: "
        f"{len(baseline_only)}"
    )

    print(
        f"CANDIDATE ONLY: "
        f"{len(candidate_only)}"
    )

    print()
    print("-" * 135)
    print("COMMON TRANSACTIONS")
    print("-" * 135)

    for index in common_entries:

        baseline_trade = baseline_map[index]
        candidate_trade = candidate_map[index]

        delta = (
            candidate_trade["profit"]
            - baseline_trade["profit"]
        )

        print(
            f"INDEX={index:4d} | "
            f"BASELINE "
            f"{baseline_trade['side']:>4} "
            f"{baseline_trade['entry']:>5}->{baseline_trade['exit']:>5} "
            f"P/L={baseline_trade['profit']:+8.4f} | "
            f"CANDIDATE "
            f"{candidate_trade['side']:>4} "
            f"{candidate_trade['entry']:>5}->{candidate_trade['exit']:>5} "
            f"P/L={candidate_trade['profit']:+8.4f} | "
            f"DELTA={delta:+8.4f}"
        )

    print()
    print("-" * 135)
    print("BASELINE-ONLY TRANSACTIONS")
    print("-" * 135)

    for index in baseline_only:

        info = baseline_map[index]

        print(
            f"INDEX={index:4d} | "
            f"{info['side']:>4} "
            f"{info['entry']:>5}->{info['exit']:>5} | "
            f"P/L={info['profit']:+.4f}"
        )

    print(
        f"BASELINE-ONLY TOTAL P/L: "
        f"{baseline_only_profit:+.4f}"
    )

    print()
    print("-" * 135)
    print("CANDIDATE-ONLY TRANSACTIONS")
    print("-" * 135)

    for index in candidate_only:

        info = candidate_map[index]

        print(
            f"INDEX={index:4d} | "
            f"{info['side']:>4} "
            f"{info['entry']:>5}->{info['exit']:>5} | "
            f"P/L={info['profit']:+.4f}"
        )

    print(
        f"CANDIDATE-ONLY TOTAL P/L: "
        f"{candidate_only_profit:+.4f}"
    )

    print()
    print("-" * 135)
    print("PROFIT DECOMPOSITION")
    print("-" * 135)

    print(
        f"COMMON BASELINE P/L: "
        f"{common_baseline_profit:+.4f}"
    )

    print(
        f"COMMON CANDIDATE P/L: "
        f"{common_candidate_profit:+.4f}"
    )

    print(
        f"COMMON TRANSACTION DELTA: "
        f"{common_candidate_profit - common_baseline_profit:+.4f}"
    )

    print(
        f"BASELINE-ONLY P/L: "
        f"{baseline_only_profit:+.4f}"
    )

    print(
        f"CANDIDATE-ONLY P/L: "
        f"{candidate_only_profit:+.4f}"
    )

    reconstructed_delta = (
        common_candidate_profit
        + candidate_only_profit
        - common_baseline_profit
        - baseline_only_profit
    )

    print(
        f"RECONSTRUCTED DELTA: "
        f"{reconstructed_delta:+.4f}"
    )

    print(
        f"ACTUAL DELTA: "
        f"{actual_total_delta:+.4f}"
    )

    print()
    print("-" * 135)
    print("BEST / WORST UNIQUE TRANSACTIONS")
    print("-" * 135)

    candidate_sorted = sorted(
        candidate_only,
        key=lambda index: candidate_map[index]["profit"],
        reverse=True
    )

    baseline_sorted = sorted(
        baseline_only,
        key=lambda index: baseline_map[index]["profit"],
        reverse=True
    )

    print()
    print("CANDIDATE ONLY — BEST:")

    for index in candidate_sorted[:5]:

        info = candidate_map[index]

        print(
            f"INDEX={index:4d} | "
            f"{info['side']:>4} "
            f"{info['entry']:>5}->{info['exit']:>5} | "
            f"P/L={info['profit']:+.4f}"
        )

    print()
    print("CANDIDATE ONLY — WORST:")

    for index in candidate_sorted[-5:]:

        info = candidate_map[index]

        print(
            f"INDEX={index:4d} | "
            f"{info['side']:>4} "
            f"{info['entry']:>5}->{info['exit']:>5} | "
            f"P/L={info['profit']:+.4f}"
        )

    print()
    print("BASELINE ONLY — BEST:")

    for index in baseline_sorted[:5]:

        info = baseline_map[index]

        print(
            f"INDEX={index:4d} | "
            f"{info['side']:>4} "
            f"{info['entry']:>5}->{info['exit']:>5} | "
            f"P/L={info['profit']:+.4f}"
        )

    print()
    print("BASELINE ONLY — WORST:")

    for index in baseline_sorted[-5:]:

        info = baseline_map[index]

        print(
            f"INDEX={index:4d} | "
            f"{info['side']:>4} "
            f"{info['entry']:>5}->{info['exit']:>5} | "
            f"P/L={info['profit']:+.4f}"
        )

    print()
    print("=" * 135)
    print(f"{name} | END")
    print("=" * 135)


def main():

    print()
    print("=" * 135)
    print("BASELINE vs CANDIDATE — UNIQUE TRANSACTION ANALYSIS")
    print(
        f"BASELINE=30/70 | "
        f"CANDIDATE=35.50/68.50 | "
        f"FEE={TRADING_FEE:.4f} | "
        f"MIN_DIFF={MIN_DIFFERENCE:.2f} | "
        f"RSI={RSI_METHOD}"
    )
    print("=" * 135)

    for name, path in DATASETS.items():

        analyze_dataset(
            name,
            path
        )


if __name__ == "__main__":
    main()
