from src.data.data_provider import DataProvider
from src.backtest.backtest_runner import BacktestRunner


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALIDATION": "data/backtest/BTCUSDT_1m_validation_5000.json",
    "TEST": "data/backtest/BTCUSDT_1m_test_5000.json",
}


RSI_VALUES = [
    34.50,
    35.00,
    35.05,
    35.10,
    35.15,
    35.20,
    35.25,
    35.30,
    35.35,
    35.40,
    35.45,
    35.50,
    35.55,
    35.60,
    35.65,
    35.70,
    35.75,
]


BASE_RSI = 34.50


def run_backtest(path, buy_rsi):
    runner = BacktestRunner(
        symbol="BTCUSDT",
        interval="1m",
        limit=5000,
        initial_balance=1000.0,
        buy_rsi=buy_rsi,
        sell_rsi=70.0,
        min_difference=1.0,
        trading_fee=0.0,
        rsi_method="classic",
        data_source="file",
        data_file=path,
    )

    runner.load_data()
    runner.run()

    return runner


def main():
    provider = DataProvider()

    results = {}

    for dataset_name, path in DATASETS.items():

        print()
        print("#" * 125)
        print(f"{dataset_name} | FINE BUY RSI SWEEP")
        print("#" * 125)

        dataset_results = {}

        for buy_rsi in RSI_VALUES:

            runner = run_backtest(
                path,
                buy_rsi
            )

            engine = runner.backtest_engine

            dataset_results[buy_rsi] = {
                "trades": engine.get_trade_count(),
                "profit": engine.get_total_profit(),
                "pf": engine.get_profit_factor(),
                "dd": engine.get_max_drawdown(),
                "wr": engine.get_win_rate(),
                "exp": engine.get_expectancy(),
            }

        results[dataset_name] = dataset_results

        base = dataset_results[BASE_RSI]

        print()
        print(
            "RSI      TRADES      PROFIT       DELTA       PF       "
            "DD        WR       EXP"
        )
        print("-" * 105)

        for buy_rsi in RSI_VALUES:

            r = dataset_results[buy_rsi]

            print(
                f"{buy_rsi:5.2f}    "
                f"{r['trades']:5d}    "
                f"{r['profit']:+10.4f}    "
                f"{r['profit'] - base['profit']:+9.4f}    "
                f"{r['pf']:7.4f}    "
                f"{r['dd']:8.4f}    "
                f"{r['wr']:6.2f}%    "
                f"{r['exp']:+8.4f}"
            )

    print()
    print("#" * 125)
    print("CROSS-DATASET FINE SWEEP")
    print("#" * 125)

    print()
    print(
        "RSI      "
        "TRAIN PROFIT   "
        "VALID PROFIT   "
        "TEST PROFIT    "
        "TRAIN PF   "
        "VALID PF   "
        "TEST PF     "
        "TOTAL PROFIT"
    )
    print("-" * 125)

    for buy_rsi in RSI_VALUES:

        train = results["TRAIN"][buy_rsi]
        validation = results["VALIDATION"][buy_rsi]
        test = results["TEST"][buy_rsi]

        total_profit = (
            train["profit"]
            + validation["profit"]
            + test["profit"]
        )

        print(
            f"{buy_rsi:5.2f}    "
            f"{train['profit']:+11.4f}   "
            f"{validation['profit']:+11.4f}   "
            f"{test['profit']:+11.4f}   "
            f"{train['pf']:8.4f}   "
            f"{validation['pf']:8.4f}   "
            f"{test['pf']:8.4f}   "
            f"{total_profit:+11.4f}"
        )

    print()
    print("#" * 125)
    print("STABILITY WINDOWS")
    print("#" * 125)

    for dataset_name in DATASETS:

        dataset = results[dataset_name]

        print()
        print(dataset_name)

        previous = None
        start = None

        for buy_rsi in RSI_VALUES:

            current = (
                dataset[buy_rsi]["trades"],
                round(dataset[buy_rsi]["profit"], 8),
                round(dataset[buy_rsi]["pf"], 8),
                round(dataset[buy_rsi]["dd"], 8),
            )

            if current != previous:

                if previous is not None:
                    print(
                        f"  {start:.2f} -> "
                        f"{buy_rsi - 0.05:.2f} | "
                        f"TRADES={previous[0]} | "
                        f"PROFIT={previous[1]:+.4f} | "
                        f"PF={previous[2]:.4f} | "
                        f"DD={previous[3]:.4f}"
                    )

                start = buy_rsi
                previous = current

        if previous is not None:
            print(
                f"  {start:.2f} -> "
                f"{RSI_VALUES[-1]:.2f} | "
                f"TRADES={previous[0]} | "
                f"PROFIT={previous[1]:+.4f} | "
                f"PF={previous[2]:.4f} | "
                f"DD={previous[3]:.4f}"
            )


if __name__ == "__main__":
    main()
