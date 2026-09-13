from src.backtest.backtest_runner import BacktestRunner


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALIDATION": "data/backtest/BTCUSDT_1m_validation_5000.json",
    "TEST": "data/backtest/BTCUSDT_1m_test_5000.json",
}


BUY_VALUES = [
    34.00,
    34.10,
    34.20,
    34.25,
    34.30,
    34.35,
    34.40,
    34.45,
    34.49,
    34.50,
    34.51,
    34.55,
    34.60,
    34.70,
    34.75,
    35.00,
    35.25,
]


SELL_RSI = 68.50
FEE = 0.0004
MIN_DIFFERENCE = 1.0


def run(path, buy_rsi):

    runner = BacktestRunner(
        symbol="BTCUSDT",
        interval="1m",
        limit=5000,
        initial_balance=1000.0,
        buy_rsi=buy_rsi,
        sell_rsi=SELL_RSI,
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
    print("MICRO BUY RSI SWEEP")
    print(
        f"SELL={SELL_RSI:.2f} | "
        f"FEE={FEE:.4f} | "
        f"MIN_DIFF={MIN_DIFFERENCE:.2f} | "
        f"RSI=classic"
    )
    print("=" * 120)

    all_results = {}

    for dataset, path in DATASETS.items():

        print()
        print(dataset)
        print("-" * 120)

        print(
            f"{'BUY':>10} | "
            f"{'PROFIT':>12} | "
            f"{'TRADES':>6}"
        )

        print("-" * 120)

        dataset_results = []

        for buy in BUY_VALUES:

            profit, trades = run(
                path,
                buy
            )

            dataset_results.append(
                (buy, profit, trades)
            )

            print(
                f"{buy:10.2f} | "
                f"{profit:+12.4f} | "
                f"{trades:6d}"
            )

        all_results[dataset] = dataset_results

    print()
    print("=" * 120)
    print("CROSS-DATASET")
    print("=" * 120)

    print(
        f"{'BUY':>10} | "
        f"{'TRAIN':>12} | "
        f"{'VALID':>12} | "
        f"{'TEST':>12} | "
        f"{'TOTAL':>12} | "
        f"{'WORST':>12} | "
        f"{'AVG':>12} | "
        f"{'+DATA':>5}"
    )

    print("-" * 120)

    for i, buy in enumerate(BUY_VALUES):

        train = all_results["TRAIN"][i][1]
        valid = all_results["VALIDATION"][i][1]
        test = all_results["TEST"][i][1]

        values = [
            train,
            valid,
            test,
        ]

        total = sum(values)
        worst = min(values)
        avg = total / 3.0
        positive = sum(
            value > 0
            for value in values
        )

        print(
            f"{buy:10.2f} | "
            f"{train:+12.4f} | "
            f"{valid:+12.4f} | "
            f"{test:+12.4f} | "
            f"{total:+12.4f} | "
            f"{worst:+12.4f} | "
            f"{avg:+12.4f} | "
            f"{positive:5d}"
        )

    print()
    print("=" * 120)
    print("END")
    print("=" * 120)


if __name__ == "__main__":
    main()
