from src.backtest.backtest_runner import BacktestRunner


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALIDATION": "data/backtest/BTCUSDT_1m_validation_5000.json",
    "TEST": "data/backtest/BTCUSDT_1m_test_5000.json",
}

BASE_BUY = 34.50
BASE_SELL = 68.50

BUY_VALUES = [
    30.00,
    31.00,
    32.00,
    32.50,
    33.00,
    33.50,
    34.00,
    34.50,
]

SELL_VALUES = [
    68.50,
    69.00,
    69.50,
    70.00,
    70.50,
    71.00,
    72.00,
]


def run_test(dataset_name, path, buy_rsi, sell_rsi):
    runner = BacktestRunner(
        symbol="BTCUSDT",
        interval="1m",
        limit=5000,
        initial_balance=1000.0,
        buy_rsi=buy_rsi,
        sell_rsi=sell_rsi,
        min_difference=1.0,
        trading_fee=0.0004,
        rsi_method="classic",
        risk_percent=5.0,
        max_daily_loss_percent=10.0,
        risk_reward_ratio=2.0,
        data_source="file",
        data_file=path,
    )

    runner.run()

    return {
        "trades": runner.get_trade_count(),
        "wr": runner.get_win_rate(),
        "profit": runner.get_total_profit(),
        "pf": runner.get_profit_factor(),
        "dd": runner.get_max_drawdown(),
        "expectancy": runner.get_expectancy(),
    }


def print_result(label, results):
    print(
        f"{label:8s} | "
        f"TR={results['trades']:2d} | "
        f"WR={results['wr']:6.2f}% | "
        f"PROFIT={results['profit']:9.4f} | "
        f"PF={results['pf']:7.4f} | "
        f"DD={results['dd']:8.4f} | "
        f"EXP={results['expectancy']:8.4f}"
    )


def main():

    print("=" * 120)
    print("=== INCREMENTAL RSI THRESHOLD TEST ===")
    print("=" * 120)

    # ==========================================================
    # SELL TEST
    # ==========================================================

    print("\n" + "=" * 120)
    print("SELL RSI INCREMENTAL TEST")
    print("=" * 120)

    print(
        "SELL     | DATASET    | TR | WR       | PROFIT    | PF      | DD       | EXP"
    )
    print("-" * 120)

    sell_results = {}

    for sell_rsi in SELL_VALUES:

        sell_results[sell_rsi] = {}

        print(f"\n--- SELL RSI = {sell_rsi:.2f} ---")

        for dataset_name, path in DATASETS.items():

            result = run_test(
                dataset_name,
                path,
                BASE_BUY,
                sell_rsi,
            )

            sell_results[sell_rsi][dataset_name] = result

            print(
                f"{sell_rsi:7.2f} | "
                f"{dataset_name:10s} | "
                f"{result['trades']:2d} | "
                f"{result['wr']:7.2f}% | "
                f"{result['profit']:9.4f} | "
                f"{result['pf']:7.4f} | "
                f"{result['dd']:8.4f} | "
                f"{result['expectancy']:8.4f}"
            )

    # ==========================================================
    # SELL SUMMARY
    # ==========================================================

    print("\n" + "=" * 120)
    print("SELL SUMMARY")
    print("=" * 120)

    print(
        "SELL     | TRAIN PROF | VALID PROF | TEST PROF | "
        "TRAIN PF | VALID PF | TEST PF"
    )
    print("-" * 120)

    for sell_rsi in SELL_VALUES:

        tr = sell_results[sell_rsi]["TRAIN"]
        va = sell_results[sell_rsi]["VALIDATION"]
        te = sell_results[sell_rsi]["TEST"]

        print(
            f"{sell_rsi:7.2f} | "
            f"{tr['profit']:10.4f} | "
            f"{va['profit']:11.4f} | "
            f"{te['profit']:9.4f} | "
            f"{tr['pf']:8.4f} | "
            f"{va['pf']:8.4f} | "
            f"{te['pf']:7.4f}"
        )

    # ==========================================================
    # BUY TEST
    # ==========================================================

    print("\n" + "=" * 120)
    print("BUY RSI INCREMENTAL TEST")
    print("=" * 120)

    print(
        "BUY      | DATASET    | TR | WR       | PROFIT    | PF      | DD       | EXP"
    )
    print("-" * 120)

    buy_results = {}

    for buy_rsi in BUY_VALUES:

        buy_results[buy_rsi] = {}

        print(f"\n--- BUY RSI = {buy_rsi:.2f} ---")

        for dataset_name, path in DATASETS.items():

            result = run_test(
                dataset_name,
                path,
                buy_rsi,
                BASE_SELL,
            )

            buy_results[buy_rsi][dataset_name] = result

            print(
                f"{buy_rsi:7.2f} | "
                f"{dataset_name:10s} | "
                f"{result['trades']:2d} | "
                f"{result['wr']:7.2f}% | "
                f"{result['profit']:9.4f} | "
                f"{result['pf']:7.4f} | "
                f"{result['dd']:8.4f} | "
                f"{result['expectancy']:8.4f}"
            )

    # ==========================================================
    # BUY SUMMARY
    # ==========================================================

    print("\n" + "=" * 120)
    print("BUY SUMMARY")
    print("=" * 120)

    print(
        "BUY      | TRAIN PROF | VALID PROF | TEST PROF | "
        "TRAIN PF | VALID PF | TEST PF"
    )
    print("-" * 120)

    for buy_rsi in BUY_VALUES:

        tr = buy_results[buy_rsi]["TRAIN"]
        va = buy_results[buy_rsi]["VALIDATION"]
        te = buy_results[buy_rsi]["TEST"]

        print(
            f"{buy_rsi:7.2f} | "
            f"{tr['profit']:10.4f} | "
            f"{va['profit']:11.4f} | "
            f"{te['profit']:9.4f} | "
            f"{tr['pf']:8.4f} | "
            f"{va['pf']:8.4f} | "
            f"{te['pf']:7.4f}"
        )


if __name__ == "__main__":
    main()
