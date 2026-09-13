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

    trades = runner.get_trades()

    profits = [
        float(trade["profit"])
        for trade in trades
    ]

    return runner, profits


def profit_after_removing_best(profits, count):

    if len(profits) <= count:
        return sum(profits)

    ordered = sorted(profits, reverse=True)

    return sum(ordered[count:])


def profit_after_removing_worst(profits, count):

    if len(profits) <= count:
        return sum(profits)

    ordered = sorted(profits)

    return sum(ordered[count:])


def analyze(name, profits):

    total = sum(profits)
    trades = len(profits)

    wins = [
        p for p in profits
        if p > 0
    ]

    losses = [
        p for p in profits
        if p < 0
    ]

    best = max(profits)
    worst = min(profits)

    avg = total / trades if trades else 0.0
    med = median(profits) if profits else 0.0

    avg_win = (
        sum(wins) / len(wins)
        if wins else 0.0
    )

    avg_loss = (
        sum(losses) / len(losses)
        if losses else 0.0
    )

    win_rate = (
        len(wins) / trades * 100.0
        if trades else 0.0
    )

    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))

    profit_factor = (
        gross_profit / gross_loss
        if gross_loss > 0
        else float("inf")
    )

    top1 = sorted(
        profits,
        reverse=True
    )[:1]

    top3 = sorted(
        profits,
        reverse=True
    )[:3]

    top1_sum = sum(top1)
    top3_sum = sum(top3)

    top1_share = (
        top1_sum / total * 100.0
        if total > 0
        else 0.0
    )

    top3_share = (
        top3_sum / total * 100.0
        if total > 0
        else 0.0
    )

    print()
    print(
        f"{name:<10} | "
        f"TRADES={trades:2d} | "
        f"PROFIT={total:+9.4f} | "
        f"WR={win_rate:6.2f}% | "
        f"PF={profit_factor:6.3f}"
    )

    print(
        f"{'':<10} | "
        f"AVG={avg:+9.4f} | "
        f"MEDIAN={med:+9.4f} | "
        f"AVG WIN={avg_win:+9.4f} | "
        f"AVG LOSS={avg_loss:+9.4f}"
    )

    print(
        f"{'':<10} | "
        f"BEST={best:+9.4f} | "
        f"WORST={worst:+9.4f}"
    )

    print(
        f"{'':<10} | "
        f"TOP1={top1_sum:+9.4f} "
        f"({top1_share:6.2f}% total)"
    )

    print(
        f"{'':<10} | "
        f"TOP3={top3_sum:+9.4f} "
        f"({top3_share:6.2f}% total)"
    )

    print()
    print(
        f"{'':<10} | "
        f"WITHOUT BEST 1  = "
        f"{profit_after_removing_best(profits, 1):+.4f}"
    )

    print(
        f"{'':<10} | "
        f"WITHOUT BEST 2  = "
        f"{profit_after_removing_best(profits, 2):+.4f}"
    )

    print(
        f"{'':<10} | "
        f"WITHOUT BEST 3  = "
        f"{profit_after_removing_best(profits, 3):+.4f}"
    )

    print(
        f"{'':<10} | "
        f"WITHOUT WORST 1 = "
        f"{profit_after_removing_worst(profits, 1):+.4f}"
    )


def main():

    print()
    print("=" * 120)
    print("TRADE QUALITY / PROFIT CONCENTRATION")
    print(
        "BASELINE=30/70 | "
        "CANDIDATE=35.50/68.50 | "
        f"FEE={FEE:.4f} | "
        f"MIN_DIFF={MIN_DIFFERENCE:.2f}"
    )
    print("=" * 120)

    all_results = {}

    for dataset, path in DATASETS.items():

        print()
        print("=" * 120)
        print(dataset)
        print("=" * 120)

        all_results[dataset] = {}

        for strategy, (buy, sell) in STRATEGIES.items():

            runner, profits = run_strategy(
                path,
                buy,
                sell
            )

            all_results[dataset][strategy] = profits

            analyze(
                strategy,
                profits
            )

        baseline = all_results[dataset]["BASELINE"]
        candidate = all_results[dataset]["CANDIDATE"]

        print()
        print("-" * 120)
        print("CANDIDATE vs BASELINE")
        print("-" * 120)

        baseline_total = sum(baseline)
        candidate_total = sum(candidate)

        print(
            f"TOTAL ADVANTAGE: "
            f"{candidate_total - baseline_total:+.4f}"
        )

        print(
            f"CANDIDATE WITHOUT BEST 1: "
            f"{profit_after_removing_best(candidate, 1):+.4f}"
        )

        print(
            f"CANDIDATE WITHOUT BEST 3: "
            f"{profit_after_removing_best(candidate, 3):+.4f}"
        )

    print()
    print("=" * 120)
    print("END")
    print("=" * 120)


if __name__ == "__main__":
    main()
