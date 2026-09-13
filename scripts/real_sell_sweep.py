from src.backtest.backtest_runner import BacktestRunner


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALIDATION": "data/backtest/BTCUSDT_1m_validation_5000.json",
    "TEST": "data/backtest/BTCUSDT_1m_test_5000.json",
}

BUY_RSI = 35.50
MIN_DIFFERENCE = 1.0
TRADING_FEE = 0.0
RSI_METHOD = "classic"


SELL_VALUES = [
    round(68.0 + i * 0.25, 2)
    for i in range(41)
]


def run_backtest(data_file, sell_rsi):
    runner = BacktestRunner(
        symbol="BTCUSDT",
        interval="1m",
        limit=5000,
        initial_balance=1000.0,
        buy_rsi=BUY_RSI,
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

    results = []

    print()
    print("=" * 115)
    print("REAL SELL RSI SWEEP")
    print(
        f"BUY={BUY_RSI:.2f} | "
        f"SELL=68.00..78.00 | STEP=0.25 | "
        f"MIN_DIFF={MIN_DIFFERENCE:.2f}"
    )
    print("=" * 115)

    for sell_rsi in SELL_VALUES:

        row = {
            "SELL": sell_rsi,
            "TRAIN": None,
            "VALIDATION": None,
            "TEST": None,
        }

        for dataset_name, data_file in DATASETS.items():

            runner = run_backtest(
                data_file,
                sell_rsi
            )

            row[dataset_name] = {
                "profit": runner.get_total_profit(),
                "pf": runner.get_profit_factor(),
                "dd": runner.get_max_drawdown(),
                "trades": len(runner.get_trades()),
                "wr": runner.get_win_rate(),
                "expectancy": runner.get_expectancy(),
            }

        total_profit = sum(
            row[name]["profit"]
            for name in DATASETS
        )

        worst_profit = min(
            row[name]["profit"]
            for name in DATASETS
        )

        avg_profit = total_profit / 3.0

        row["TOTAL"] = total_profit
        row["WORST"] = worst_profit
        row["AVG"] = avg_profit

        results.append(row)

    print()
    print("=" * 150)
    print(
        "SELL RSI | "
        "TRAIN PROF | VALID PROF | TEST PROF | "
        "TOTAL | WORST | AVG | "
        "TRAIN PF | VALID PF | TEST PF | "
        "TRADES T/V/T"
    )
    print("=" * 150)

    for row in results:

        train = row["TRAIN"]
        valid = row["VALIDATION"]
        test = row["TEST"]

        print(
            f"{row['SELL']:7.2f} | "
            f"{train['profit']:10.4f} | "
            f"{valid['profit']:10.4f} | "
            f"{test['profit']:9.4f} | "
            f"{row['TOTAL']:9.4f} | "
            f"{row['WORST']:9.4f} | "
            f"{row['AVG']:8.4f} | "
            f"{train['pf']:8.4f} | "
            f"{valid['pf']:8.4f} | "
            f"{test['pf']:7.4f} | "
            f"{train['trades']:2d}/{valid['trades']:2d}/{test['trades']:2d}"
        )

    print()
    print("=" * 150)
    print("TOP 10 BY TOTAL PROFIT")
    print("=" * 150)

    top_total = sorted(
        results,
        key=lambda x: x["TOTAL"],
        reverse=True
    )[:10]

    for rank, row in enumerate(top_total, 1):

        print(
            f"{rank:2d}. "
            f"SELL={row['SELL']:5.2f} | "
            f"TOTAL={row['TOTAL']:+10.4f} | "
            f"WORST={row['WORST']:+10.4f} | "
            f"TRAIN={row['TRAIN']['profit']:+9.4f} | "
            f"VALID={row['VALIDATION']['profit']:+9.4f} | "
            f"TEST={row['TEST']['profit']:+9.4f}"
        )

    print()
    print("=" * 150)
    print("TOP 10 BY WORST-DATASET PROFIT")
    print("=" * 150)

    top_worst = sorted(
        results,
        key=lambda x: x["WORST"],
        reverse=True
    )[:10]

    for rank, row in enumerate(top_worst, 1):

        print(
            f"{rank:2d}. "
            f"SELL={row['SELL']:5.2f} | "
            f"WORST={row['WORST']:+10.4f} | "
            f"TOTAL={row['TOTAL']:+10.4f} | "
            f"TRAIN={row['TRAIN']['profit']:+9.4f} | "
            f"VALID={row['VALIDATION']['profit']:+9.4f} | "
            f"TEST={row['TEST']['profit']:+9.4f}"
        )

    print()
    print("=" * 150)
    print("TOP 10 BY AVERAGE PROFIT")
    print("=" * 150)

    top_avg = sorted(
        results,
        key=lambda x: x["AVG"],
        reverse=True
    )[:10]

    for rank, row in enumerate(top_avg, 1):

        print(
            f"{rank:2d}. "
            f"SELL={row['SELL']:5.2f} | "
            f"AVG={row['AVG']:+10.4f} | "
            f"TOTAL={row['TOTAL']:+10.4f} | "
            f"WORST={row['WORST']:+10.4f}"
        )

    print()
    print("=" * 150)
    print("BEST CANDIDATE")
    print("=" * 150)

    robust = max(
        results,
        key=lambda x: (
            x["WORST"],
            x["TOTAL"],
            x["AVG"]
        )
    )

    print(
        f"SELL={robust['SELL']:.2f} | "
        f"TOTAL={robust['TOTAL']:+.4f} | "
        f"WORST={robust['WORST']:+.4f} | "
        f"AVG={robust['AVG']:+.4f}"
    )

    print()
    print(
        "UWAGA: BEST CANDIDATE jest wybierany najpierw po "
        "najlepszym najgorszym zbiorze (WORST), a dopiero potem "
        "po TOTAL i AVG."
    )


if __name__ == "__main__":
    main()
