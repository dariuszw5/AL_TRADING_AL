from src.backtest.backtest_runner import BacktestRunner


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALIDATION": "data/backtest/BTCUSDT_1m_validation_5000.json",
    "TEST": "data/backtest/BTCUSDT_1m_test_5000.json",
}


SELL_VALUES = [
    68.25,
    68.30,
    68.35,
    68.40,
    68.41,
    68.415,
    68.4155,
    68.4156,
    68.41565,
    68.41566,
    68.4157,
    68.4158,
    68.416,
    68.42,
    68.425,
    68.43,
    68.45,
    68.50,
]


BUY_RSI = 34.50
FEE = 0.0004
MIN_DIFFERENCE = 1.0


def run(path, sell_rsi):

    runner = BacktestRunner(
        symbol="BTCUSDT",
        interval="1m",
        limit=5000,
        initial_balance=1000.0,
        buy_rsi=BUY_RSI,
        sell_rsi=sell_rsi,
        min_difference=MIN_DIFFERENCE,
        trading_fee=FEE,
        rsi_method="classic",
        data_source="file",
        data_file=path,
    )

    runner.load_data()
    runner.run()

    result = runner.get_backtest_result()

    profit = result.balance - result.initial_balance

    return profit, len(result.trades)


def main():

    print()
    print("=" * 120)
    print("MICRO SELL RSI SWEEP")
    print(
        f"BUY={BUY_RSI:.2f} | "
        f"FEE={FEE:.4f} | "
        f"MIN_DIFF={MIN_DIFFERENCE:.2f} | "
        f"RSI=classic"
    )
    print("=" * 120)

    all_results = {}

    for dataset, path in DATASETS.items():

        print()
        print(f"{dataset}")
        print("-" * 120)
        print(
            f"{'SELL':>10} | "
            f"{'PROFIT':>12} | "
            f"{'TRADES':>6}"
        )
        print("-" * 120)

        dataset_results = []

        for sell in SELL_VALUES:

            profit, trades = run(path, sell)

            dataset_results.append(
                (sell, profit, trades)
            )

            print(
                f"{sell:10.5f} | "
                f"{profit:+12.4f} | "
                f"{trades:6d}"
            )

        all_results[dataset] = dataset_results

    print()
    print("=" * 120)
    print("CROSS-DATASET")
    print("=" * 120)

    print(
        f"{'SELL':>10} | "
        f"{'TRAIN':>12} | "
        f"{'VALID':>12} | "
        f"{'TEST':>12} | "
        f"{'TOTAL':>12} | "
        f"{'WORST':>12} | "
        f"{'+DATA':>5}"
    )

    print("-" * 120)

    for i, sell in enumerate(SELL_VALUES):

        train = all_results["TRAIN"][i][1]
        valid = all_results["VALIDATION"][i][1]
        test = all_results["TEST"][i][1]

        values = [train, valid, test]

        total = sum(values)
        worst = min(values)
        positive = sum(v > 0 for v in values)

        print(
            f"{sell:10.5f} | "
            f"{train:+12.4f} | "
            f"{valid:+12.4f} | "
            f"{test:+12.4f} | "
            f"{total:+12.4f} | "
            f"{worst:+12.4f} | "
            f"{positive:5d}"
        )

    print()
    print("=" * 120)
    print("END")
    print("=" * 120)


if __name__ == "__main__":
    main()
