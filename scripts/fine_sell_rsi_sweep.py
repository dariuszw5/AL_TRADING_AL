from src.backtest.backtest_runner import BacktestRunner


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALIDATION": "data/backtest/BTCUSDT_1m_validation_5000.json",
    "TEST": "data/backtest/BTCUSDT_1m_test_5000.json",
}


BUY_RSI = 35.50

SELL_RSI_VALUES = [
    68.00,
    68.25,
    68.50,
    68.75,
    69.00,
    69.25,
    69.50,
    69.75,
    70.00,
    70.25,
    70.50,
    70.75,
    71.00,
    71.25,
    71.50,
    71.75,
    72.00,
    72.25,
    72.50,
    72.75,
    73.00,
    73.25,
    73.50,
    73.75,
    74.00,
    74.25,
    74.50,
    74.75,
    75.00,
    75.25,
    75.50,
    75.75,
    76.00,
    76.25,
    76.50,
    76.75,
    77.00,
    77.25,
    77.50,
    77.75,
    78.00,
]


BASE_SELL_RSI = 70.0


def run_backtest(path, sell_rsi):
    runner = BacktestRunner(
        symbol="BTCUSDT",
        interval="1m",
        limit=5000,
        initial_balance=1000.0,
        buy_rsi=BUY_RSI,
        sell_rsi=sell_rsi,
        min_difference=1.0,
        trading_fee=0.0,
        rsi_method="classic",
        data_source="file",
        data_file=path,
    )

    runner.load_data()
    runner.run()

    engine = runner.backtest_engine

    return {
        "trades": engine.get_trade_count(),
        "profit": engine.get_total_profit(),
        "pf": engine.get_profit_factor(),
        "dd": engine.get_max_drawdown(),
        "wr": engine.get_win_rate(),
        "exp": engine.get_expectancy(),
    }


def main():
    all_results = {}

    for dataset_name, path in DATASETS.items():

        print()
        print("#" * 125)
        print(f"{dataset_name} | FINE SELL RSI SWEEP")
        print("#" * 125)

        dataset_results = {}

        for sell_rsi in SELL_RSI_VALUES:
            dataset_results[sell_rsi] = run_backtest(
                path,
                sell_rsi
            )

        all_results[dataset_name] = dataset_results

        base = dataset_results[BASE_SELL_RSI]

        print()
        print(
            "SELL RSI   TRADES      PROFIT       DELTA       PF       "
            "DD        WR       EXP"
        )
        print("-" * 110)

        for sell_rsi in SELL_RSI_VALUES:

            r = dataset_results[sell_rsi]

            print(
                f"{sell_rsi:7.2f}    "
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
    print("CROSS-DATASET FINE SELL RSI SUMMARY")
    print("#" * 125)

    print()
    print(
        "SELL RSI   "
        "TRAIN PROFIT   "
        "VALID PROFIT   "
        "TEST PROFIT    "
        "TRAIN PF   "
        "VALID PF   "
        "TEST PF     "
        "TOTAL PROFIT"
    )
    print("-" * 125)

    for sell_rsi in SELL_RSI_VALUES:

        train = all_results["TRAIN"][sell_rsi]
        validation = all_results["VALIDATION"][sell_rsi]
        test = all_results["TEST"][sell_rsi]

        total_profit = (
            train["profit"]
            + validation["profit"]
            + test["profit"]
        )

        print(
            f"{sell_rsi:7.2f}   "
            f"{train['profit']:+11.4f}   "
            f"{validation['profit']:+11.4f}   "
            f"{test['profit']:+11.4f}   "
            f"{train['pf']:8.4f}   "
            f"{validation['pf']:8.4f}   "
            f"{test['pf']:8.4f}   "
            f"{total_profit:+11.4f}"
        )


if __name__ == "__main__":
    main()
