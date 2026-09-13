from src.backtest.backtest_runner import BacktestRunner


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALIDATION": "data/backtest/BTCUSDT_1m_validation_5000.json",
    "TEST": "data/backtest/BTCUSDT_1m_test_5000.json",
}


BUY_VALUES = [
    34.00,
    34.25,
    34.50,
    34.75,
]

SELL_VALUES = [
    68.40,
    68.41570,
    68.50,
    68.75,
    69.00,
]


FEE = 0.0004
MIN_DIFFERENCE = 1.0


def run(path, buy_rsi, sell_rsi):

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
    print("BUY x SELL STABILITY MATRIX")
    print(
        f"FEE={FEE:.4f} | "
        f"MIN_DIFF={MIN_DIFFERENCE:.2f} | "
        f"RSI=classic"
    )
    print("=" * 120)

    results = {}

    for dataset, path in DATASETS.items():

        print()
        print("=" * 120)
        print(dataset)
        print("=" * 120)

        dataset_results = {}

        for buy in BUY_VALUES:

            dataset_results[buy] = {}

            for sell in SELL_VALUES:

                profit, trades = run(
                    path,
                    buy,
                    sell,
                )

                dataset_results[buy][sell] = (
                    profit,
                    trades,
                )

                print(
                    f"BUY={buy:6.2f} | "
                    f"SELL={sell:8.5f} | "
                    f"PROFIT={profit:+10.4f} | "
                    f"TRADES={trades:2d}"
                )

        results[dataset] = dataset_results

    print()
    print("=" * 120)
    print("CROSS-DATASET RANKING")
    print("=" * 120)

    rows = []

    for buy in BUY_VALUES:

        for sell in SELL_VALUES:

            train = results["TRAIN"][buy][sell][0]
            valid = results["VALIDATION"][buy][sell][0]
            test = results["TEST"][buy][sell][0]

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

            rows.append(
                (
                    total,
                    worst,
                    avg,
                    positive,
                    buy,
                    sell,
                    train,
                    valid,
                    test,
                )
            )

    rows.sort(
        key=lambda x: (
            x[3],
            x[1],
            x[0],
        ),
        reverse=True,
    )

    print(
        f"{'R':>3} | "
        f"{'BUY':>7} | "
        f"{'SELL':>9} | "
        f"{'TRAIN':>11} | "
        f"{'VALID':>11} | "
        f"{'TEST':>11} | "
        f"{'TOTAL':>11} | "
        f"{'WORST':>11} | "
        f"{'AVG':>11} | "
        f"{'+DATA':>5}"
    )

    print("-" * 120)

    for rank, row in enumerate(rows, 1):

        (
            total,
            worst,
            avg,
            positive,
            buy,
            sell,
            train,
            valid,
            test,
        ) = row

        print(
            f"{rank:3d} | "
            f"{buy:7.2f} | "
            f"{sell:9.5f} | "
            f"{train:+11.4f} | "
            f"{valid:+11.4f} | "
            f"{test:+11.4f} | "
            f"{total:+11.4f} | "
            f"{worst:+11.4f} | "
            f"{avg:+11.4f} | "
            f"{positive:5d}"
        )

    print()
    print("=" * 120)
    print("END")
    print("=" * 120)


if __name__ == "__main__":
    main()
