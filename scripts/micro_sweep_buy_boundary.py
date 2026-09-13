from src.backtest.backtest_runner import BacktestRunner


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALIDATION": "data/backtest/BTCUSDT_1m_validation_5000.json",
    "TEST": "data/backtest/BTCUSDT_1m_test_5000.json",
}

SELL_RSI = 68.50
FEE = 0.0004
MIN_DIFF = 1.0
RSI_METHOD = "classic"


# ------------------------------------------------------------
# Dokładne okolice wykrytych granic
# ------------------------------------------------------------

BUY_VALUES = [
    # okolica VALIDATION: RSI = 34.124397649
    34.05,
    34.08,
    34.09,
    34.10,
    34.11,
    34.12,
    34.121,
    34.122,
    34.123,
    34.124,
    34.1243,
    34.12439,
    34.124397,
    34.1243976,
    34.1243977,
    34.1244,
    34.125,
    34.126,
    34.13,
    34.15,
    34.20,

    # szeroka okolica TEST
    34.40,
    34.44,
    34.45,
    34.451,
    34.452,
    34.4527,
    34.45278,
    34.452789,
    34.4527896,
    34.4527897,
    34.4527898,
    34.45279,
    34.453,
    34.454,
    34.46,
    34.47,
    34.48,
    34.49,
    34.50,
]


def run(dataset, buy_rsi):
    runner = BacktestRunner(
        symbol="BTCUSDT",
        interval="1m",
        limit=5000,
        initial_balance=1000.0,
        buy_rsi=buy_rsi,
        sell_rsi=SELL_RSI,
        min_difference=MIN_DIFF,
        trading_fee=FEE,
        rsi_method=RSI_METHOD,
        data_source="file",
        data_file=DATASETS[dataset],
    )

    runner.load_data()
    runner.run()

    result = runner.get_backtest_result()

    return result


all_results = {
    dataset: []
    for dataset in DATASETS
}


print()
print("=" * 120)
print("BUY MICRO-SWEEP")
print(
    f"SELL={SELL_RSI:.2f} | FEE={FEE:.4f} | "
    f"MIN_DIFF={MIN_DIFF:.2f} | RSI={RSI_METHOD}"
)
print("=" * 120)


# ------------------------------------------------------------
# Backtest wszystkich wartości
# ------------------------------------------------------------

for buy_rsi in BUY_VALUES:

    print(f"Testing BUY={buy_rsi:.7f} ...")

    for dataset in DATASETS:

        result = run(dataset, buy_rsi)

        profit = result.balance - result.initial_balance

        if result.trades:
            wins = sum(
                1 for trade in result.trades
                if trade["profit"] > 0
            )

            win_rate = wins / len(result.trades) * 100.0
        else:
            win_rate = 0.0

        all_results[dataset].append({
            "buy": buy_rsi,
            "profit": profit,
            "trades": len(result.trades),
            "win_rate": win_rate,
        })


# ------------------------------------------------------------
# Tabele
# ------------------------------------------------------------

for dataset in DATASETS:

    print()
    print("=" * 120)
    print(f"{dataset}")
    print("=" * 120)

    print(
        f"{'BUY':>12} "
        f"{'PROFIT':>12} "
        f"{'TRADES':>8} "
        f"{'WR %':>10}"
    )

    print("-" * 120)

    for row in all_results[dataset]:

        print(
            f"{row['buy']:12.7f} "
            f"{row['profit']:+12.4f} "
            f"{row['trades']:8d} "
            f"{row['win_rate']:10.2f}"
        )


# ------------------------------------------------------------
# CROSS-DATASET
# ------------------------------------------------------------

print()
print("=" * 120)
print("CROSS-DATASET RANKING")
print("=" * 120)

cross = []

for buy_rsi in BUY_VALUES:

    rows = {}

    for dataset in DATASETS:
        row = next(
            x for x in all_results[dataset]
            if abs(x["buy"] - buy_rsi) < 1e-12
        )

        rows[dataset] = row

    total = sum(
        rows[dataset]["profit"]
        for dataset in DATASETS
    )

    worst = min(
        rows[dataset]["profit"]
        for dataset in DATASETS
    )

    average = total / len(DATASETS)

    positive_count = sum(
        1
        for dataset in DATASETS
        if rows[dataset]["profit"] > 0
    )

    cross.append({
        "buy": buy_rsi,
        "train": rows["TRAIN"]["profit"],
        "validation": rows["VALIDATION"]["profit"],
        "test": rows["TEST"]["profit"],
        "total": total,
        "worst": worst,
        "average": average,
        "positive": positive_count,
    })


cross_sorted = sorted(
    cross,
    key=lambda x: (
        x["worst"],
        x["total"],
    ),
    reverse=True,
)


print(
    f"{'BUY':>12} "
    f"{'TRAIN':>12} "
    f"{'VALID':>12} "
    f"{'TEST':>12} "
    f"{'TOTAL':>12} "
    f"{'WORST':>12} "
    f"{'AVG':>12} "
    f"{'+DATA':>8}"
)

print("-" * 120)

for row in cross_sorted:

    print(
        f"{row['buy']:12.7f} "
        f"{row['train']:+12.4f} "
        f"{row['validation']:+12.4f} "
        f"{row['test']:+12.4f} "
        f"{row['total']:+12.4f} "
        f"{row['worst']:+12.4f} "
        f"{row['average']:+12.4f} "
        f"{row['positive']:>4}/3"
    )


# ------------------------------------------------------------
# IDENTYCZNE PLATEAU
# ------------------------------------------------------------

print()
print("=" * 120)
print("IDENTICAL PROFIT PLATEAUS")
print("=" * 120)


for dataset in DATASETS:

    rows = all_results[dataset]

    groups = []

    current = None

    for row in rows:

        if current is None:
            current = {
                "start": row["buy"],
                "end": row["buy"],
                "profit": row["profit"],
                "trades": row["trades"],
            }

        elif (
            abs(row["profit"] - current["profit"]) < 1e-9
            and row["trades"] == current["trades"]
        ):
            current["end"] = row["buy"]

        else:
            groups.append(current)

            current = {
                "start": row["buy"],
                "end": row["buy"],
                "profit": row["profit"],
                "trades": row["trades"],
            }

    if current is not None:
        groups.append(current)

    print()
    print(dataset)

    for group in groups:

        if group["start"] != group["end"]:

            print(
                f"  {group['start']:.7f}"
                f" -> "
                f"{group['end']:.7f}"
                f" | PROFIT={group['profit']:+.4f}"
                f" | TRADES={group['trades']}"
            )


# ------------------------------------------------------------
# Najlepszy kandydat wg worst-case
# ------------------------------------------------------------

best_worst = max(
    cross,
    key=lambda x: (
        x["worst"],
        x["total"],
    ),
)

best_total = max(
    cross,
    key=lambda x: x["total"]
)

print()
print("=" * 120)
print("BEST CANDIDATES")
print("=" * 120)

print(
    f"WORST-CASE BEST: BUY={best_worst['buy']:.7f} "
    f"| TOTAL={best_worst['total']:+.4f} "
    f"| WORST={best_worst['worst']:+.4f}"
)

print(
    f"TOTAL BEST:      BUY={best_total['buy']:.7f} "
    f"| TOTAL={best_total['total']:+.4f} "
    f"| WORST={best_total['worst']:+.4f}"
)

print()
print("=" * 120)
print("END")
print("=" * 120)
