from src.backtest.backtest_runner import BacktestRunner


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALIDATION": "data/backtest/BTCUSDT_1m_validation_5000.json",
    "TEST": "data/backtest/BTCUSDT_1m_test_5000.json",
}

BUY_VALUES = [
    33.50,
    34.00,
    34.25,
    34.50,
    34.75,
    35.00,
    35.50,
]

SELL_VALUES = [
    68.00,
    68.25,
    68.50,
    68.75,
    69.00,
    69.50,
    70.00,
]

FEE = 0.0004
MIN_DIFF = 1.0
RSI_METHOD = "classic"


def run(dataset, buy_rsi, sell_rsi):
    runner = BacktestRunner(
        symbol="BTCUSDT",
        interval="1m",
        limit=5000,
        initial_balance=1000.0,
        buy_rsi=buy_rsi,
        sell_rsi=sell_rsi,
        min_difference=MIN_DIFF,
        trading_fee=FEE,
        rsi_method=RSI_METHOD,
        data_source="file",
        data_file=DATASETS[dataset],
    )

    runner.load_data()
    runner.run()

    return runner.get_backtest_result()


results = []


print()
print("=" * 150)
print("BUY x SELL PARAMETER STABILITY")
print(
    f"FEE={FEE:.4f} | MIN_DIFF={MIN_DIFF:.2f} | "
    f"RSI={RSI_METHOD}"
)
print("=" * 150)


for buy in BUY_VALUES:

    for sell in SELL_VALUES:

        print(
            f"Testing BUY={buy:.2f} SELL={sell:.2f} ..."
        )

        profits = {}

        for dataset in DATASETS:

            result = run(
                dataset,
                buy,
                sell,
            )

            profits[dataset] = (
                result.balance
                - result.initial_balance
            )

        total = sum(profits.values())
        worst = min(profits.values())
        average = total / 3.0

        positive = sum(
            1
            for profit in profits.values()
            if profit > 0
        )

        results.append({
            "buy": buy,
            "sell": sell,
            "train": profits["TRAIN"],
            "validation": profits["VALIDATION"],
            "test": profits["TEST"],
            "total": total,
            "worst": worst,
            "average": average,
            "positive": positive,
        })


print()
print("=" * 150)
print("ALL RESULTS SORTED BY TOTAL")
print("=" * 150)

sorted_total = sorted(
    results,
    key=lambda x: (
        x["total"],
        x["worst"],
    ),
    reverse=True,
)

print(
    f"{'RANK':>6} "
    f"{'BUY':>8} "
    f"{'SELL':>8} "
    f"{'TRAIN':>12} "
    f"{'VALID':>12} "
    f"{'TEST':>12} "
    f"{'TOTAL':>12} "
    f"{'WORST':>12} "
    f"{'+DATA':>8}"
)

print("-" * 150)

for rank, row in enumerate(sorted_total, 1):

    print(
        f"{rank:6d} "
        f"{row['buy']:8.2f} "
        f"{row['sell']:8.2f} "
        f"{row['train']:+12.4f} "
        f"{row['validation']:+12.4f} "
        f"{row['test']:+12.4f} "
        f"{row['total']:+12.4f} "
        f"{row['worst']:+12.4f} "
        f"{row['positive']:>4}/3"
    )


print()
print("=" * 150)
print("TOP 10 BY WORST-CASE")
print("=" * 150)

sorted_worst = sorted(
    results,
    key=lambda x: (
        x["worst"],
        x["total"],
    ),
    reverse=True,
)

print(
    f"{'RANK':>6} "
    f"{'BUY':>8} "
    f"{'SELL':>8} "
    f"{'TRAIN':>12} "
    f"{'VALID':>12} "
    f"{'TEST':>12} "
    f"{'TOTAL':>12} "
    f"{'WORST':>12} "
    f"{'+DATA':>8}"
)

print("-" * 150)

for rank, row in enumerate(sorted_worst[:10], 1):

    print(
        f"{rank:6d} "
        f"{row['buy']:8.2f} "
        f"{row['sell']:8.2f} "
        f"{row['train']:+12.4f} "
        f"{row['validation']:+12.4f} "
        f"{row['test']:+12.4f} "
        f"{row['total']:+12.4f} "
        f"{row['worst']:+12.4f} "
        f"{row['positive']:>4}/3"
    )


print()
print("=" * 150)
print("STABLE POSITIVE REGION")
print("=" * 150)

stable = [
    row
    for row in results
    if row["positive"] == 3
]

print(
    f"Combinations positive on TRAIN + VALIDATION + TEST: "
    f"{len(stable)} / {len(results)}"
)

if stable:

    best_stable_total = max(
        stable,
        key=lambda x: (
            x["total"],
            x["worst"],
        )
    )

    best_stable_worst = max(
        stable,
        key=lambda x: (
            x["worst"],
            x["total"],
        )
    )

    print(
        f"BEST TOTAL: "
        f"BUY={best_stable_total['buy']:.2f} "
        f"SELL={best_stable_total['sell']:.2f} "
        f"TOTAL={best_stable_total['total']:+.4f} "
        f"WORST={best_stable_total['worst']:+.4f}"
    )

    print(
        f"BEST WORST: "
        f"BUY={best_stable_worst['buy']:.2f} "
        f"SELL={best_stable_worst['sell']:.2f} "
        f"TOTAL={best_stable_worst['total']:+.4f} "
        f"WORST={best_stable_worst['worst']:+.4f}"
    )


print()
print("=" * 150)
print("LOCAL REGION AROUND 34.50 / 68.50")
print("=" * 150)

local = [
    row
    for row in results
    if row["buy"] in [34.00, 34.25, 34.50, 34.75]
    and row["sell"] in [68.25, 68.50, 68.75, 69.00]
]

local = sorted(
    local,
    key=lambda x: (
        x["total"],
        x["worst"],
    ),
    reverse=True,
)

for row in local:

    print(
        f"BUY={row['buy']:.2f} "
        f"SELL={row['sell']:.2f} | "
        f"TOTAL={row['total']:+.4f} | "
        f"WORST={row['worst']:+.4f} | "
        f"TRAIN={row['train']:+.4f} | "
        f"VALID={row['validation']:+.4f} | "
        f"TEST={row['test']:+.4f} | "
        f"+DATA={row['positive']}/3"
    )


print()
print("=" * 150)
print("END")
print("=" * 150)
