from src.backtest.backtest_runner import BacktestRunner


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALIDATION": "data/backtest/BTCUSDT_1m_validation_5000.json",
    "TEST": "data/backtest/BTCUSDT_1m_test_5000.json",
}

BUY_RSI = 34.50
SELL_RSI = 68.50

MIN_DIFF_VALUES = [
    0.00,
    0.25,
    0.50,
    0.75,
    1.00,
    1.25,
    1.50,
    2.00,
]


def run_test(path, min_difference):
    runner = BacktestRunner(
        symbol="BTCUSDT",
        interval="1m",
        limit=5000,
        initial_balance=1000.0,
        buy_rsi=BUY_RSI,
        sell_rsi=SELL_RSI,
        min_difference=min_difference,
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
        "exp": runner.get_expectancy(),
    }


def main():

    print("=" * 120)
    print("=== MIN_DIFF ROBUSTNESS TEST ===")
    print("=== BUY=34.50 | SELL=68.50 | CLASSIC | FEE=0.0004 | TIME=240 ===")
    print("=" * 120)

    results = {}

    for min_diff in MIN_DIFF_VALUES:

        results[min_diff] = {}

        print(f"\n--- MIN_DIFF = {min_diff:.2f} ---")

        for name, path in DATASETS.items():

            r = run_test(path, min_diff)
            results[min_diff][name] = r

            print(
                f"{name:10s} | "
                f"TR={r['trades']:2d} | "
                f"WR={r['wr']:6.2f}% | "
                f"PROFIT={r['profit']:9.4f} | "
                f"PF={r['pf']:7.4f} | "
                f"DD={r['dd']:8.4f} | "
                f"EXP={r['exp']:8.4f}"
            )

    print("\n" + "=" * 120)
    print("=== SUMMARY ===")
    print("=" * 120)

    print(
        "DIFF   | TRAIN PROF | VALID PROF | TEST PROF | "
        "TOTAL PROF | TRAIN PF | VALID PF | TEST PF"
    )
    print("-" * 120)

    for min_diff in MIN_DIFF_VALUES:

        tr = results[min_diff]["TRAIN"]
        va = results[min_diff]["VALIDATION"]
        te = results[min_diff]["TEST"]

        total = (
            tr["profit"] +
            va["profit"] +
            te["profit"]
        )

        print(
            f"{min_diff:5.2f} | "
            f"{tr['profit']:10.4f} | "
            f"{va['profit']:11.4f} | "
            f"{te['profit']:9.4f} | "
            f"{total:10.4f} | "
            f"{tr['pf']:8.4f} | "
            f"{va['pf']:8.4f} | "
            f"{te['pf']:7.4f}"
        )


if __name__ == "__main__":
    main()
