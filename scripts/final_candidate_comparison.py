from src.backtest.backtest_runner import BacktestRunner


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALIDATION": "data/backtest/BTCUSDT_1m_validation_5000.json",
    "TEST": "data/backtest/BTCUSDT_1m_test_5000.json",
}

CANDIDATES = [
    ("BASE", 30.00, 70.00),
    ("OLD", 35.50, 68.50),
    ("NEW_TOTAL", 34.05, 68.50),
    ("NEW_WORST", 34.50, 68.50),
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


def metrics(result):
    trades = result.trades

    profits = [
        trade["profit"]
        for trade in trades
    ]

    wins = [
        p for p in profits
        if p > 0
    ]

    losses = [
        p for p in profits
        if p < 0
    ]

    total_profit = sum(profits)

    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))

    if gross_loss > 0:
        profit_factor = gross_profit / gross_loss
    else:
        profit_factor = float("inf")

    win_rate = (
        len(wins) / len(trades) * 100.0
        if trades
        else 0.0
    )

    avg_win = (
        sum(wins) / len(wins)
        if wins
        else 0.0
    )

    avg_loss = (
        sum(losses) / len(losses)
        if losses
        else 0.0
    )

    expectancy = (
        total_profit / len(trades)
        if trades
        else 0.0
    )

    equity = result.equity_curve

    peak = equity[0] if equity else 0.0
    max_drawdown = 0.0

    for value in equity:
        if value > peak:
            peak = value

        drawdown = peak - value

        if drawdown > max_drawdown:
            max_drawdown = drawdown

    return {
        "profit": total_profit,
        "pf": profit_factor,
        "dd": max_drawdown,
        "wr": win_rate,
        "trades": len(trades),
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "expectancy": expectancy,
    }


all_results = {}


print()
print("=" * 150)
print("FINAL CANDIDATE COMPARISON")
print(
    f"FEE={FEE:.4f} | MIN_DIFF={MIN_DIFF:.2f} | "
    f"RSI={RSI_METHOD}"
)
print("=" * 150)


for name, buy_rsi, sell_rsi in CANDIDATES:

    print()
    print(
        f"Testing {name}: "
        f"BUY={buy_rsi:.2f} SELL={sell_rsi:.2f}"
    )

    all_results[name] = {}

    for dataset in DATASETS:

        result = run(
            dataset,
            buy_rsi,
            sell_rsi,
        )

        all_results[name][dataset] = metrics(result)


print()
print("=" * 150)
print("DETAILED RESULTS")
print("=" * 150)


for name, buy_rsi, sell_rsi in CANDIDATES:

    print()
    print(
        f"--- {name} | BUY={buy_rsi:.2f} "
        f"SELL={sell_rsi:.2f} ---"
    )

    print(
        f"{'DATASET':<14}"
        f"{'PROFIT':>12}"
        f"{'PF':>10}"
        f"{'DD':>12}"
        f"{'WR':>10}"
        f"{'TRADES':>10}"
        f"{'AVG WIN':>12}"
        f"{'AVG LOSS':>12}"
        f"{'EXPECT':>12}"
    )

    print("-" * 150)

    for dataset in DATASETS:

        m = all_results[name][dataset]

        print(
            f"{dataset:<14}"
            f"{m['profit']:+12.4f}"
            f"{m['pf']:10.4f}"
            f"{m['dd']:12.4f}"
            f"{m['wr']:10.2f}"
            f"{m['trades']:10d}"
            f"{m['avg_win']:+12.4f}"
            f"{m['avg_loss']:+12.4f}"
            f"{m['expectancy']:+12.4f}"
        )


print()
print("=" * 150)
print("AGGREGATE RESULTS")
print("=" * 150)

print(
    f"{'CANDIDATE':<14}"
    f"{'TOTAL':>14}"
    f"{'WORST':>14}"
    f"{'AVERAGE':>14}"
    f"{'+DATA':>10}"
    f"{'TRADES':>12}"
)

print("-" * 150)


aggregate = {}

for name, buy_rsi, sell_rsi in CANDIDATES:

    profits = [
        all_results[name][dataset]["profit"]
        for dataset in DATASETS
    ]

    trades = [
        all_results[name][dataset]["trades"]
        for dataset in DATASETS
    ]

    total = sum(profits)
    worst = min(profits)
    average = total / 3.0
    positive = sum(
        1 for p in profits
        if p > 0
    )

    aggregate[name] = {
        "total": total,
        "worst": worst,
        "average": average,
        "positive": positive,
        "trades": sum(trades),
    }

    print(
        f"{name:<14}"
        f"{total:+14.4f}"
        f"{worst:+14.4f}"
        f"{average:+14.4f}"
        f"{positive:>6}/3"
        f"{sum(trades):>12d}"
    )


base = aggregate["BASE"]

print()
print("=" * 150)
print("IMPROVEMENT VS BASE")
print("=" * 150)

for name, _, _ in CANDIDATES:

    if name == "BASE":
        continue

    current = aggregate[name]

    print(
        f"{name:<14}"
        f"TOTAL DELTA={current['total'] - base['total']:+.4f} | "
        f"WORST DELTA={current['worst'] - base['worst']:+.4f} | "
        f"AVG DELTA={current['average'] - base['average']:+.4f}"
    )


print()
print("=" * 150)
print("END")
print("=" * 150)
