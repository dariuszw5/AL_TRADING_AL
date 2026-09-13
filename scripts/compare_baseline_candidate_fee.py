from src.backtest.backtest_runner import BacktestRunner


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALIDATION": "data/backtest/BTCUSDT_1m_validation_5000.json",
    "TEST": "data/backtest/BTCUSDT_1m_test_5000.json",
}


STRATEGIES = {
    "BASELINE": {
        "buy": 30.00,
        "sell": 70.00,
    },
    "CANDIDATE": {
        "buy": 35.50,
        "sell": 68.50,
    },
}


MIN_DIFFERENCE = 1.0
RSI_METHOD = "classic"
TRADING_FEE = 0.0004


def run_backtest(data_file, buy_rsi, sell_rsi):

    runner = BacktestRunner(
        symbol="BTCUSDT",
        interval="1m",
        limit=5000,
        initial_balance=1000.0,
        buy_rsi=buy_rsi,
        sell_rsi=sell_rsi,
        min_difference=MIN_DIFFERENCE,
        trading_fee=TRADING_FEE,
        rsi_method=RSI_METHOD,
        data_source="file",
        data_file=data_file,
    )

    runner.load_data()
    runner.run()

    return runner


def main():

    print()
    print("=" * 135)
    print("BASELINE vs CANDIDATE")
    print(
        f"FEE={TRADING_FEE:.4f} | "
        f"MIN_DIFF={MIN_DIFFERENCE:.2f} | "
        f"RSI={RSI_METHOD}"
    )
    print("=" * 135)

    results = {}

    for strategy_name, config in STRATEGIES.items():

        results[strategy_name] = {}

        for dataset_name, data_file in DATASETS.items():

            runner = run_backtest(
                data_file,
                config["buy"],
                config["sell"],
            )

            results[strategy_name][dataset_name] = {
                "profit": runner.get_total_profit(),
                "pf": runner.get_profit_factor(),
                "dd": runner.get_max_drawdown(),
                "wr": runner.get_win_rate(),
                "trades": len(runner.get_trades()),
                "final": runner.get_balance(),
            }

    print()
    print("=" * 150)
    print(
        "STRATEGY   | DATASET     | BUY   | SELL  | "
        "PROFIT     | PF     | DD       | WR     | TRADES | FINAL"
    )
    print("=" * 150)

    for strategy_name, config in STRATEGIES.items():

        for dataset_name in DATASETS:

            r = results[strategy_name][dataset_name]

            print(
                f"{strategy_name:10s} | "
                f"{dataset_name:11s} | "
                f"{config['buy']:5.2f} | "
                f"{config['sell']:5.2f} | "
                f"{r['profit']:+10.4f} | "
                f"{r['pf']:6.4f} | "
                f"{r['dd']:8.4f} | "
                f"{r['wr']:6.2f}% | "
                f"{r['trades']:6d} | "
                f"{r['final']:10.4f}"
            )

    print()
    print("=" * 150)
    print("AGGREGATE COMPARISON")
    print("=" * 150)

    for strategy_name in STRATEGIES:

        total_profit = sum(
            results[strategy_name][dataset]["profit"]
            for dataset in DATASETS
        )

        worst_profit = min(
            results[strategy_name][dataset]["profit"]
            for dataset in DATASETS
        )

        avg_profit = total_profit / 3.0

        total_trades = sum(
            results[strategy_name][dataset]["trades"]
            for dataset in DATASETS
        )

        print(
            f"{strategy_name:10s} | "
            f"TOTAL={total_profit:+.4f} | "
            f"WORST={worst_profit:+.4f} | "
            f"AVG={avg_profit:+.4f} | "
            f"TRADES={total_trades}"
        )

    print()
    print("=" * 150)
    print("CANDIDATE ADVANTAGE OVER BASELINE")
    print("=" * 150)

    for dataset_name in DATASETS:

        base = results["BASELINE"][dataset_name]
        candidate = results["CANDIDATE"][dataset_name]

        profit_delta = candidate["profit"] - base["profit"]
        pf_delta = candidate["pf"] - base["pf"]
        dd_delta = candidate["dd"] - base["dd"]
        wr_delta = candidate["wr"] - base["wr"]
        trade_delta = candidate["trades"] - base["trades"]

        print(
            f"{dataset_name:11s} | "
            f"PROFIT DELTA={profit_delta:+.4f} | "
            f"PF DELTA={pf_delta:+.4f} | "
            f"DD DELTA={dd_delta:+.4f} | "
            f"WR DELTA={wr_delta:+.2f} pp | "
            f"TRADES DELTA={trade_delta:+d}"
        )

    base_total = sum(
        results["BASELINE"][dataset]["profit"]
        for dataset in DATASETS
    )

    candidate_total = sum(
        results["CANDIDATE"][dataset]["profit"]
        for dataset in DATASETS
    )

    base_worst = min(
        results["BASELINE"][dataset]["profit"]
        for dataset in DATASETS
    )

    candidate_worst = min(
        results["CANDIDATE"][dataset]["profit"]
        for dataset in DATASETS
    )

    print()
    print("=" * 150)
    print("FINAL VERDICT")
    print("=" * 150)

    print(
        f"BASELINE  TOTAL={base_total:+.4f} | "
        f"WORST={base_worst:+.4f}"
    )

    print(
        f"CANDIDATE TOTAL={candidate_total:+.4f} | "
        f"WORST={candidate_worst:+.4f}"
    )

    print(
        f"TOTAL ADVANTAGE={candidate_total - base_total:+.4f}"
    )

    print(
        f"WORST DATASET ADVANTAGE={candidate_worst - base_worst:+.4f}"
    )


if __name__ == "__main__":
    main()
