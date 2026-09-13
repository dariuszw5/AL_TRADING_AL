from src.backtest.backtest_runner import BacktestRunner


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALIDATION": "data/backtest/BTCUSDT_1m_validation_5000.json",
    "TEST": "data/backtest/BTCUSDT_1m_test_5000.json",
}

BUY_VALUES = [
    34.05,
    34.25,
    34.50,
]

SELL_RSI = 68.50
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


def run(dataset, buy_rsi, fee):
    runner = BacktestRunner(
        symbol="BTCUSDT",
        interval="1m",
        limit=5000,
        initial_balance=1000.0,
        buy_rsi=buy_rsi,
        sell_rsi=SELL_RSI,
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
print("=" * 120)
print("BUY FEE ROBUSTNESS")
print(
    f"SELL={SELL_RSI:.2f} | MIN_DIFF={MIN_DIFF:.2f} | "
    f"RSI={RSI_METHOD}"
)
print("=" * 120)


for buy in BUY_VALUES:

    for fee in FEES:

        print(
            f"Testing BUY={buy:.2f} FEE={fee:.4f} ..."
        )

        dataset_results = {}

        for dataset in DATASETS:

            result = run(dataset, buy, fee)

            profit = result.balance - result.initial_balance

            wins = sum(
                1
                for trade in result.trades
                if trade["profit"] > 0
            )

            if result.trades:
                win_rate = (
                    wins / len(result.trades) * 100.0
                )
            else:
                win_rate = 0.0

            dataset_results[dataset] = {
                "profit": profit,
                "trades": len(result.trades),
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
            "buy": buy,
            "fee": fee,
            "train": dataset_results["TRAIN"],
            "validation": dataset_results["VALIDATION"],
            "test": dataset_results["TEST"],
            "total": total,
            "worst": worst,
            "average": average,
            "positive": positive,
        })


# ------------------------------------------------------------
# Szczegółowa tabela dla każdego BUY
# ------------------------------------------------------------

for buy in BUY_VALUES:

    print()
    print("=" * 120)
    print(f"BUY = {buy:.2f}")
    print("=" * 120)

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

    print("-" * 120)

    for row in results:

        if row["buy"] != buy:
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


# ------------------------------------------------------------
# Porównanie kandydatów przy każdym fee
# ------------------------------------------------------------

print()
print("=" * 120)
print("BEST BUY FOR EACH FEE")
print("=" * 120)

for fee in FEES:

    rows = [
        row
        for row in results
        if abs(row["fee"] - fee) < 1e-12
    ]

    best_total = max(
        rows,
        key=lambda x: x["total"]
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
        f"TOTAL BEST=BUY {best_total['buy']:.2f} "
        f"({best_total['total']:+.4f}) | "
        f"WORST BEST=BUY {best_worst['buy']:.2f} "
        f"({best_worst['worst']:+.4f})"
    )


# ------------------------------------------------------------
# Czy kandydaci pozostają dodatni na wszystkich datasetach?
# ------------------------------------------------------------

print()
print("=" * 120)
print("POSITIVE ACROSS ALL DATASETS")
print("=" * 120)

for buy in BUY_VALUES:

    positive_fees = []

    for fee in FEES:

        row = next(
            row
            for row in results
            if row["buy"] == buy
            and abs(row["fee"] - fee) < 1e-12
        )

        if row["positive"] == 3:
            positive_fees.append(fee)

    if positive_fees:

        print(
            f"BUY={buy:.2f} | "
            f"positive 3/3 through fee={max(positive_fees):.4f}"
        )

    else:

        print(
            f"BUY={buy:.2f} | "
            f"NO fee with positive 3/3"
        )


# ------------------------------------------------------------
# Podsumowanie
# ------------------------------------------------------------

print()
print("=" * 120)
print("SUMMARY")
print("=" * 120)

for buy in BUY_VALUES:

    subset = [
        row
        for row in results
        if row["buy"] == buy
    ]

    max_fee_all_positive = max(
        (
            row["fee"]
            for row in subset
            if row["positive"] == 3
        ),
        default=None,
    )

    total_at_0004 = next(
        row
        for row in subset
        if abs(row["fee"] - 0.0004) < 1e-12
    )

    total_at_0005 = next(
        row
        for row in subset
        if abs(row["fee"] - 0.0005) < 1e-12
    )

    print(
        f"BUY={buy:.2f} | "
        f"FEE .0004 TOTAL={total_at_0004['total']:+.4f} "
        f"WORST={total_at_0004['worst']:+.4f} | "
        f"FEE .0005 TOTAL={total_at_0005['total']:+.4f} "
        f"WORST={total_at_0005['worst']:+.4f} | "
        f"3/3 THROUGH={max_fee_all_positive:.4f}"
        if max_fee_all_positive is not None
        else
        f"BUY={buy:.2f} | "
        f"NO 3/3 POSITIVE FEE"
    )


print()
print("=" * 120)
print("END")
print("=" * 120)
