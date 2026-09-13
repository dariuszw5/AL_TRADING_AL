from src.backtest.backtest_runner import BacktestRunner


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALIDATION": "data/backtest/BTCUSDT_1m_validation_5000.json",
    "TEST": "data/backtest/BTCUSDT_1m_test_5000.json",
}

STRATEGIES = {
    "BASELINE": (30.00, 70.00),
    "CANDIDATE": (33.8, 68.50),
}

FEE = 0.0004
MIN_DIFFERENCE = 1.0

WINDOW = 1000
STEP = 250


def run_strategy(data_file, buy_rsi, sell_rsi):

    runner = BacktestRunner(
        symbol="BTCUSDT",
        interval="1m",
        limit=5000,
        initial_balance=1000.0,
        buy_rsi=buy_rsi,
        sell_rsi=sell_rsi,
        min_difference=MIN_DIFFERENCE,
        trading_fee=FEE,
        rsi_method="classic",
        data_source="file",
        data_file=data_file,
    )

    runner.load_data()
    runner.run()

    return runner


def candle_index(candles, timestamp):

    for i, candle in enumerate(candles):

        if candle.timestamp == timestamp:
            return i

    return None


def prepare_trades(runner):

    trades = []

    for number, trade in enumerate(
        runner.get_trades(),
        start=1
    ):

        entry_index = candle_index(
            runner.candles,
            trade.get("entry_timestamp")
        )

        exit_index = candle_index(
            runner.candles,
            trade.get("exit_timestamp")
        )

        trades.append({
            "number": number,
            "entry": entry_index,
            "exit": exit_index,
            "side": trade.get(
                "side",
                trade.get("signal", "?")
            ),
            "profit": float(
                trade.get("profit", 0.0)
            ),
            "exit_reason": trade.get(
                "exit_reason",
                "?"
            ),
        })

    return trades


def window_statistics(
    trades,
    start,
    end
):

    selected = [
        trade
        for trade in trades
        if trade["exit"] is not None
        and start <= trade["exit"] <= end
    ]

    profits = [
        trade["profit"]
        for trade in selected
    ]

    total_profit = sum(profits)

    wins = [
        p for p in profits
        if p > 0
    ]

    losses = [
        p for p in profits
        if p < 0
    ]

    gross_profit = sum(wins)

    gross_loss = abs(
        sum(losses)
    )

    if gross_loss > 0:
        pf = gross_profit / gross_loss
    elif gross_profit > 0:
        pf = float("inf")
    else:
        pf = 0.0

    if profits:
        wr = (
            len(wins) /
            len(profits) *
            100.0
        )
    else:
        wr = 0.0

    return {
        "trades": len(profits),
        "profit": total_profit,
        "pf": pf,
        "wr": wr,
    }


def fmt_pf(value):

    if value == float("inf"):
        return "   inf"

    return f"{value:6.3f}"


def analyze_dataset(
    dataset,
    trades_by_strategy
):

    print()
    print("=" * 125)
    print(
        f"{dataset} | "
        f"ROLLING WINDOW ANALYSIS"
    )
    print(
        f"WINDOW={WINDOW} | "
        f"STEP={STEP} | "
        f"P/L ASSIGNED TO EXIT"
    )
    print("=" * 125)

    headers = (
        f"{'WINDOW':>11} | "
        f"{'BASE PROF':>10} | "
        f"{'CAND PROF':>10} | "
        f"{'DELTA':>10} | "
        f"{'BASE PF':>7} | "
        f"{'CAND PF':>7} | "
        f"{'BASE WR':>7} | "
        f"{'CAND WR':>7} | "
        f"{'T/C':>5}"
    )

    print(headers)
    print("-" * 125)

    deltas = []
    candidate_wins = 0
    baseline_wins = 0
    ties = 0

    for start in range(
        0,
        5000 - WINDOW + 1,
        STEP
    ):

        end = start + WINDOW - 1

        baseline = window_statistics(
            trades_by_strategy["BASELINE"],
            start,
            end
        )

        candidate = window_statistics(
            trades_by_strategy["CANDIDATE"],
            start,
            end
        )

        delta = (
            candidate["profit"] -
            baseline["profit"]
        )

        deltas.append(delta)

        if delta > 0:
            candidate_wins += 1
        elif delta < 0:
            baseline_wins += 1
        else:
            ties += 1

        print(
            f"{start:5d}-{end:5d} | "
            f"{baseline['profit']:+10.4f} | "
            f"{candidate['profit']:+10.4f} | "
            f"{delta:+10.4f} | "
            f"{fmt_pf(baseline['pf'])} | "
            f"{fmt_pf(candidate['pf'])} | "
            f"{baseline['wr']:6.2f}% | "
            f"{candidate['wr']:6.2f}% | "
            f"{baseline['trades']:2d}/{candidate['trades']:2d}"
        )

    print()
    print(
        f"CANDIDATE WINS: "
        f"{candidate_wins}/"
        f"{len(deltas)}"
    )

    print(
        f"BASELINE WINS: "
        f"{baseline_wins}/"
        f"{len(deltas)}"
    )

    print(
        f"TIES: "
        f"{ties}/"
        f"{len(deltas)}"
    )

    positive_deltas = [
        d for d in deltas
        if d > 0
    ]

    negative_deltas = [
        d for d in deltas
        if d < 0
    ]

    print()

    if deltas:
        print(
            f"AVERAGE DELTA: "
            f"{sum(deltas) / len(deltas):+.4f}"
        )

        print(
            f"BEST WINDOW DELTA: "
            f"{max(deltas):+.4f}"
        )

        print(
            f"WORST WINDOW DELTA: "
            f"{min(deltas):+.4f}"
        )

    if positive_deltas:
        print(
            f"AVG POSITIVE DELTA: "
            f"{sum(positive_deltas) / len(positive_deltas):+.4f}"
        )

    if negative_deltas:
        print(
            f"AVG NEGATIVE DELTA: "
            f"{sum(negative_deltas) / len(negative_deltas):+.4f}"
        )


def main():

    print()
    print("=" * 125)
    print("ROLLING WINDOW ROBUSTNESS")
    print(
        "BASELINE=30/70 | "
        "CANDIDATE=33.8/68.50 | "
        f"FEE={FEE:.4f} | "
        f"MIN_DIFF={MIN_DIFFERENCE:.2f} | "
        "RSI=classic"
    )
    print("=" * 125)

    for dataset, path in DATASETS.items():

        trades_by_strategy = {}

        for strategy, (
            buy,
            sell
        ) in STRATEGIES.items():

            runner = run_strategy(
                path,
                buy,
                sell
            )

            trades_by_strategy[strategy] = (
                prepare_trades(runner)
            )

        analyze_dataset(
            dataset,
            trades_by_strategy
        )

    print()
    print("=" * 125)
    print("ROLLING WINDOW ROBUSTNESS COMPLETE")
    print("=" * 125)


if __name__ == "__main__":
    main()

