from src.backtest.backtest_runner import BacktestRunner


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALIDATION": "data/backtest/BTCUSDT_1m_validation_5000.json",
    "TEST": "data/backtest/BTCUSDT_1m_test_5000.json",
}


BUY_RSI = 35.50
SELL_RSI = 68.50
MIN_DIFFERENCE = 1.0
RSI_METHOD = "classic"

FEE_VALUES = [
    0.0,
    0.0001,
    0.0002,
    0.0004,
    0.0005,
    0.0010,
]


def run_backtest(data_file, trading_fee):

    runner = BacktestRunner(
        symbol="BTCUSDT",
        interval="1m",
        limit=5000,
        initial_balance=1000.0,
        buy_rsi=BUY_RSI,
        sell_rsi=SELL_RSI,
        min_difference=MIN_DIFFERENCE,
        trading_fee=trading_fee,
        rsi_method=RSI_METHOD,
        data_source="file",
        data_file=data_file,
    )

    runner.load_data()
    runner.run()

    return runner


def main():

    print()
    print("=" * 125)
    print("FEE ROBUSTNESS TEST")
    print(
        f"BUY={BUY_RSI:.2f} | "
        f"SELL={SELL_RSI:.2f} | "
        f"MIN_DIFF={MIN_DIFFERENCE:.2f} | "
        f"RSI={RSI_METHOD}"
    )
    print("=" * 125)

    all_results = []

    for fee in FEE_VALUES:

        dataset_results = {}

        for name, path in DATASETS.items():

            runner = run_backtest(
                path,
                fee
            )

            dataset_results[name] = {
                "profit": runner.get_total_profit(),
                "pf": runner.get_profit_factor(),
                "dd": runner.get_max_drawdown(),
                "wr": runner.get_win_rate(),
                "trades": len(runner.get_trades()),
                "final": runner.get_balance(),
            }

        total_profit = sum(
            dataset_results[name]["profit"]
            for name in DATASETS
        )

        worst_profit = min(
            dataset_results[name]["profit"]
            for name in DATASETS
        )

        avg_profit = total_profit / 3.0

        result = {
            "fee": fee,
            "datasets": dataset_results,
            "total": total_profit,
            "worst": worst_profit,
            "avg": avg_profit,
        }

        all_results.append(result)

    print()
    print("=" * 150)
    print(
        "FEE | "
        "TRAIN PROF | VALID PROF | TEST PROF | "
        "TOTAL | WORST | AVG | "
        "TRAIN PF | VALID PF | TEST PF | "
        "TRADES T/V/T"
    )
    print("=" * 150)

    for result in all_results:

        train = result["datasets"]["TRAIN"]
        valid = result["datasets"]["VALIDATION"]
        test = result["datasets"]["TEST"]

        print(
            f"{result['fee']:7.4f} | "
            f"{train['profit']:10.4f} | "
            f"{valid['profit']:10.4f} | "
            f"{test['profit']:9.4f} | "
            f"{result['total']:9.4f} | "
            f"{result['worst']:9.4f} | "
            f"{result['avg']:8.4f} | "
            f"{train['pf']:8.4f} | "
            f"{valid['pf']:8.4f} | "
            f"{test['pf']:7.4f} | "
            f"{train['trades']:2d}/{valid['trades']:2d}/{test['trades']:2d}"
        )

    print()
    print("=" * 150)
    print("FEE IMPACT RELATIVE TO FEE=0")
    print("=" * 150)

    baseline = all_results[0]

    for result in all_results:

        delta_total = (
            result["total"]
            - baseline["total"]
        )

        delta_worst = (
            result["worst"]
            - baseline["worst"]
        )

        print(
            f"FEE={result['fee']:.4f} | "
            f"TOTAL={result['total']:+.4f} | "
            f"DELTA TOTAL={delta_total:+.4f} | "
            f"WORST={result['worst']:+.4f} | "
            f"DELTA WORST={delta_worst:+.4f}"
        )

    print()
    print("=" * 150)
    print("ROBUSTNESS")
    print("=" * 150)

    for result in all_results:

        positive_all = all(
            result["datasets"][name]["profit"] > 0
            for name in DATASETS
        )

        print(
            f"FEE={result['fee']:.4f} | "
            f"ALL DATASETS POSITIVE="
            f"{'YES' if positive_all else 'NO'} | "
            f"TOTAL={result['total']:+.4f} | "
            f"WORST={result['worst']:+.4f}"
        )


if __name__ == "__main__":
    main()
