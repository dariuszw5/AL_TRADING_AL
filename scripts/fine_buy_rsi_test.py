from src.backtest.backtest_runner import BacktestRunner


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALIDATION": "data/backtest/BTCUSDT_1m_validation_5000.json",
    "TEST": "data/backtest/BTCUSDT_1m_test_5000.json",
}

SELL_RSI = 68.50

BUY_VALUES = [
    33.60, 33.70, 33.80, 33.90,
    34.00, 34.10, 34.20, 34.30, 34.40, 34.50,
    34.60, 34.70, 34.80, 34.90, 35.00,
]


def run_test(path, buy_rsi):
    runner = BacktestRunner(
        symbol="BTCUSDT",
        interval="1m",
        limit=5000,
        initial_balance=1000.0,
        buy_rsi=buy_rsi,
        sell_rsi=SELL_RSI,
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
        "exp": runner.get_expectancy(),
    }


def main():

    print("=" * 120)
    print("=== FINE BUY RSI TEST: 33.60 - 35.00 ===")
    print("=" * 120)

    results = {}

    for buy in BUY_VALUES:

        results[buy] = {}

        print(f"\n--- BUY RSI = {buy:.2f} ---")

        for name, path in DATASETS.items():

            r = run_test(path, buy)
            results[buy][name] = r

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
        "BUY    | TRAIN PROF | VALID PROF | TEST PROF | "
        "TOTAL PROF | TRAIN PF | VALID PF | TEST PF"
    )
    print("-" * 120)

    for buy in BUY_VALUES:

        tr = results[buy]["TRAIN"]
        va = results[buy]["VALIDATION"]
        te = results[buy]["TEST"]

        total = (
            tr["profit"] +
            va["profit"] +
            te["profit"]
        )

        print(
            f"{buy:5.2f} | "
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
