from src.backtest.backtest_runner import BacktestRunner


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALIDATION": "data/backtest/BTCUSDT_1m_validation_5000.json",
    "TEST": "data/backtest/BTCUSDT_1m_test_5000.json",
}

CANDIDATES = [
    (34.05, 68.50),
    (34.05, 68.75),
    (34.50, 68.50),
    (34.50, 68.75),
]

MIN_DIFF = 1.0
RSI_METHOD = "classic"

FEES = [
    0.0000,
    0.0001,
    0.0002,
    0.0003,
    0.0004,
    0.0005,
    0.0006,
    0.0008,
    0.0010,
]


def run(dataset, buy_rsi, sell_rsi, fee):
    runner = BacktestRunner(
        symbol="BTCUSDT",
        interval="1m",
        limit=5000,
        initial_balance=1000.0,
        buy_rsi=buy_rsi,
        sell_rsi=sell_rsi,
        min_difference=MIN_DIFF,
        trading_fee=fee,
        rsi_method=RSI_METHOD,
        data_source="file",
        data_file=DATASETS[dataset],
    )

    runner.load_data()
    runner.run()

    return runner.get_backtest_result()


results = []


print()
print("=" * 140)
print("FINAL BUY x SELL x FEE ROBUSTNESS")
print(
    f"MIN_DIFF={MIN_DIFF:.2f} | RSI={RSI_METHOD}"
)
print("=" * 140)


for buy_rsi, sell_rsi in CANDIDATES:

    for fee in FEES:

        print(
            f"Testing BUY={buy_rsi:.2f} "
            f"SELL={sell_rsi:.2f} "
            f"FEE={fee:.4f} ..."
        )

        dataset_results = {}

        for dataset in DATASETS:

            result = run(
                dataset,
                buy_rsi,
                sell_rsi,
                fee,
            )

            profit = (
                result.balance
                - result.initial_balance
            )

            wins = sum(
                1
                for trade in result.trades
                if trade["profit"] > 0
            )

            trades = len(result.trades)

            win_rate = (
                wins / trades * 100.0
                if trades
                else 0.0
            )

            dataset_results[dataset] = {
                "profit": profit,
                "trades": trades,
                "win_rate": win_rate,
            }

        total = sum(
            dataset_results[dataset]["profit"]
            for dataset in DATASETS
        )

        worst = min(
            dataset_results[dataset]["profit"]
            for dataset in DATASETS
        )

        average = total / 3.0

        positive = sum(
            1
            for dataset in DATASETS
            if dataset_results[dataset]["profit"] > 0
        )

        results.append({
            "buy": buy_rsi,
            "sell": sell_rsi,
            "fee": fee,
            "train": dataset_results["TRAIN"],
            "validation": dataset_results["VALIDATION"],
            "test": dataset_results["TEST"],
            "total": total,
            "worst": worst,
            "average": average,
            "positive": positive,
        })


for buy_rsi, sell_rsi in CANDIDATES:

    print()
    print("=" * 140)
    print(
        f"BUY={buy_rsi:.2f} | SELL={sell_rsi:.2f}"
    )
    print("=" * 140)

    print(
        f"{'FEE':>8} "
        f"{'TRAIN':>12} "
        f"{'VALID':>12} "
        f"{'TEST':>12} "
        f"{'TOTAL':>12} "
        f"{'WORST':>12} "
        f"{'AVG':>12} "
        f"{'+DATA':>8}"
    )

    print("-" * 140)

    for row in results:

        if (
            row["buy"] != buy_rsi
            or row["sell"] != sell_rsi
        ):
            continue

        print(
            f"{row['fee']:8.4f} "
            f"{row['train']['profit']:+12.4f} "
            f"{row['validation']['profit']:+12.4f} "
            f"{row['test']['profit']:+12.4f} "
            f"{row['total']:+12.4f} "
            f"{row['worst']:+12.4f} "
            f"{row['average']:+12.4f} "
            f"{row['positive']:>4}/3"
        )


print()
print("=" * 140)
print("BEST CANDIDATE FOR EACH FEE")
print("=" * 140)

for fee in FEES:

    rows = [
        row
        for row in results
        if abs(row["fee"] - fee) < 1e-12
    ]

    best_total = max(
        rows,
        key=lambda x: (
            x["total"],
            x["worst"],
        )
    )

    best_worst = max(
        rows,
        key=lambda x: (
            x["worst"],
            x["total"],
        )
    )

    print(
        f"FEE={fee:.4f} | "
        f"TOTAL BEST="
        f"BUY {best_total['buy']:.2f} "
        f"SELL {best_total['sell']:.2f} "
        f"({best_total['total']:+.4f}) | "
        f"WORST BEST="
        f"BUY {best_worst['buy']:.2f} "
        f"SELL {best_worst['sell']:.2f} "
        f"({best_worst['worst']:+.4f})"
    )


print()
print("=" * 140)
print("ROBUSTNESS SUMMARY")
print("=" * 140)

for buy_rsi, sell_rsi in CANDIDATES:

    subset = [
        row
        for row in results
        if (
            row["buy"] == buy_rsi
            and row["sell"] == sell_rsi
        )
    ]

    positive_rows = [
        row
        for row in subset
        if row["positive"] == 3
    ]

    max_fee_all_positive = (
        max(row["fee"] for row in positive_rows)
        if positive_rows
        else None
    )

    row_0004 = next(
        row
        for row in subset
        if abs(row["fee"] - 0.0004) < 1e-12
    )

    row_0005 = next(
        row
        for row in subset
        if abs(row["fee"] - 0.0005) < 1e-12
    )

    row_0008 = next(
        row
        for row in subset
        if abs(row["fee"] - 0.0008) < 1e-12
    )

    print(
        f"BUY={buy_rsi:.2f} SELL={sell_rsi:.2f} | "
        f".0004 TOTAL={row_0004['total']:+.4f} "
        f"WORST={row_0004['worst']:+.4f} | "
        f".0005 TOTAL={row_0005['total']:+.4f} "
        f"WORST={row_0005['worst']:+.4f} | "
        f".0008 TOTAL={row_0008['total']:+.4f} "
        f"WORST={row_0008['worst']:+.4f} | "
        f"3/3 THROUGH="
        f"{max_fee_all_positive:.4f}"
        if max_fee_all_positive is not None
        else
        f"BUY={buy_rsi:.2f} SELL={sell_rsi:.2f} | "
        f"NO 3/3 POSITIVE FEE"
    )


print()
print("=" * 140)
print("END")
print("=" * 140)
