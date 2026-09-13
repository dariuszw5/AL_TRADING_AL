from statistics import median

from src.backtest.backtest_runner import BacktestRunner


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALIDATION": "data/backtest/BTCUSDT_1m_validation_5000.json",
    "TEST": "data/backtest/BTCUSDT_1m_test_5000.json",
}

STRATEGIES = {
    "BASELINE": (30.00, 70.00),
    "CANDIDATE": (35.50, 68.50),
}

FEE = 0.0004
MIN_DIFFERENCE = 1.0
SEGMENT_SIZE = 1000


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


def leave_one_out(trades):

    total = sum(
        trade["profit"]
        for trade in trades
    )

    results = []

    for trade in trades:

        without = (
            total -
            trade["profit"]
        )

        results.append({
            "number": trade["number"],
            "entry": trade["entry"],
            "exit": trade["exit"],
            "profit": trade["profit"],
            "without": without,
        })

    return total, results


def print_leave_one_out(
    dataset,
    strategy,
    trades
):

    total, results = leave_one_out(trades)

    print()
    print("-" * 125)
    print(
        f"{dataset} | {strategy} | "
        f"LEAVE-ONE-OUT"
    )
    print("-" * 125)

    print(
        f"FULL PROFIT = {total:+.4f}"
    )

    print()

    for result in results:

        print(
            f"TRADE={result['number']:2d} | "
            f"ENTRY={str(result['entry']):>4} | "
            f"EXIT={str(result['exit']):>4} | "
            f"TRADE P/L={result['profit']:+8.4f} | "
            f"WITHOUT={result['without']:+8.4f}"
        )

    positive_without = sum(
        1
        for result in results
        if result["without"] > 0
    )

    print()
    print(
        f"POSITIVE AFTER REMOVING 1 TRADE: "
        f"{positive_without}/{len(results)}"
    )


def segment_analysis(
    dataset,
    strategy,
    trades
):

    print()
    print("-" * 125)
    print(
        f"{dataset} | {strategy} | "
        f"SEGMENT ANALYSIS"
    )
    print("-" * 125)

    total = sum(
        trade["profit"]
        for trade in trades
    )

    print(
        f"TOTAL PROFIT = {total:+.4f}"
    )

    print()

    segment_results = []

    for start in range(
        0,
        5000,
        SEGMENT_SIZE
    ):

        end = min(
            start + SEGMENT_SIZE - 1,
            4999
        )

        segment_trades = [
            trade
            for trade in trades
            if trade["entry"] is not None
            and start <= trade["entry"] <= end
        ]

        profits = [
            trade["profit"]
            for trade in segment_trades
        ]

        segment_profit = sum(profits)

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

        pf = (
            gross_profit / gross_loss
            if gross_loss > 0
            else float("inf")
        )

        win_rate = (
            len(wins) / len(profits) * 100
            if profits
            else 0.0
        )

        med = (
            median(profits)
            if profits
            else 0.0
        )

        segment_results.append(
            segment_profit
        )

        print(
            f"{start:4d}-{end:4d} | "
            f"TRADES={len(profits):2d} | "
            f"PROFIT={segment_profit:+9.4f} | "
            f"WR={win_rate:6.2f}% | "
            f"PF={pf:6.3f} | "
            f"MEDIAN={med:+8.4f}"
        )

    positive_segments = sum(
        1
        for profit in segment_results
        if profit > 0
    )

    print()
    print(
        f"POSITIVE SEGMENTS: "
        f"{positive_segments}/"
        f"{len(segment_results)}"
    )

    print(
        f"SEGMENT P/L SUM: "
        f"{sum(segment_results):+.4f}"
    )


def compare_segments(
    dataset,
    baseline_trades,
    candidate_trades
):

    print()
    print("-" * 125)
    print(
        f"{dataset} | "
        f"BASELINE vs CANDIDATE SEGMENT DELTA"
    )
    print("-" * 125)

    print(
        f"{'SEGMENT':>12} | "
        f"{'BASELINE':>12} | "
        f"{'CANDIDATE':>12} | "
        f"{'DELTA':>12}"
    )

    print("-" * 125)

    for start in range(
        0,
        5000,
        SEGMENT_SIZE
    ):

        end = min(
            start + SEGMENT_SIZE - 1,
            4999
        )

        baseline_profit = sum(
            trade["profit"]
            for trade in baseline_trades
            if trade["entry"] is not None
            and start <= trade["entry"] <= end
        )

        candidate_profit = sum(
            trade["profit"]
            for trade in candidate_trades
            if trade["entry"] is not None
            and start <= trade["entry"] <= end
        )

        delta = (
            candidate_profit -
            baseline_profit
        )

        print(
            f"{start:4d}-{end:4d} | "
            f"{baseline_profit:+12.4f} | "
            f"{candidate_profit:+12.4f} | "
            f"{delta:+12.4f}"
        )


def print_trade_distribution(
    dataset,
    strategy,
    trades
):

    profits = [
        trade["profit"]
        for trade in trades
    ]

    if not profits:
        return

    ordered = sorted(
        profits,
        reverse=True
    )

    print()
    print("-" * 125)
    print(
        f"{dataset} | {strategy} | "
        f"TRADE DISTRIBUTION"
    )
    print("-" * 125)

    for rank, profit in enumerate(
        ordered,
        start=1
    ):

        original = next(
            trade
            for trade in trades
            if trade["profit"] == profit
        )

        print(
            f"RANK={rank:2d} | "
            f"ENTRY={str(original['entry']):>4} | "
            f"EXIT={str(original['exit']):>4} | "
            f"{original['side']:>4} | "
            f"P/L={profit:+9.4f}"
        )


def main():

    print()
    print("=" * 125)
    print("ROBUSTNESS ANALYSIS")
    print(
        "BASELINE=30/70 | "
        "CANDIDATE=35.50/68.50 | "
        f"FEE={FEE:.4f} | "
        f"MIN_DIFF={MIN_DIFFERENCE:.2f} | "
        "RSI=classic"
    )
    print("=" * 125)

    for dataset, path in DATASETS.items():

        runners = {}
        trades_by_strategy = {}

        for strategy, (buy, sell) in STRATEGIES.items():

            runner = run_strategy(
                path,
                buy,
                sell
            )

            runners[strategy] = runner

            trades = prepare_trades(
                runner
            )

            trades_by_strategy[strategy] = trades

        print()
        print("=" * 125)
        print(dataset)
        print("=" * 125)

        for strategy in STRATEGIES:

            trades = trades_by_strategy[
                strategy
            ]

            print_leave_one_out(
                dataset,
                strategy,
                trades
            )

            segment_analysis(
                dataset,
                strategy,
                trades
            )

            print_trade_distribution(
                dataset,
                strategy,
                trades
            )

        compare_segments(
            dataset,
            trades_by_strategy["BASELINE"],
            trades_by_strategy["CANDIDATE"]
        )

    print()
    print("=" * 125)
    print("ROBUSTNESS ANALYSIS COMPLETE")
    print("=" * 125)


if __name__ == "__main__":
    main()
