from src.backtest.backtest_runner import BacktestRunner


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALIDATION": "data/backtest/BTCUSDT_1m_validation_5000.json",
    "TEST": "data/backtest/BTCUSDT_1m_test_5000.json",
}

BUY_RSI = 34.50
SELL_RSI = 68.50
MIN_DIFF = 1.00

TIME_VALUES = [
    180,
    195,
    210,
    225,
    240,
    255,
    270,
    285,
    300,
]


def run_test(path, max_position_candles):
    runner = BacktestRunner(
        symbol="BTCUSDT",
        interval="1m",
        limit=5000,
        initial_balance=1000.0,
        buy_rsi=BUY_RSI,
        sell_rsi=SELL_RSI,
        min_difference=MIN_DIFF,
        trading_fee=0.0004,
        rsi_method="classic",
        risk_percent=5.0,
        max_daily_loss_percent=10.0,
        risk_reward_ratio=2.0,
        data_source="file",
        data_file=path,
    )

    # max_position_candles is owned by AgentConfig,
    # not by BacktestRunner.__init__().
    runner.agent.config.max_position_candles = max_position_candles

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
    print("=== FINE TIME EXIT TEST: 180 - 300 ===")
    print("=== BUY=34.50 | SELL=68.50 | MIN_DIFF=1.00 | CLASSIC | FEE=0.0004 ===")
    print("=" * 120)

    results = {}

    for candles in TIME_VALUES:

        results[candles] = {}

        print(f"\n--- MAX_POSITION_CANDLES = {candles} ---")

        for name, path in DATASETS.items():

            r = run_test(path, candles)
            results[candles][name] = r

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
        "TIME | TRAIN PROF | VALID PROF | TEST PROF | "
        "TOTAL PROF | TRAIN PF | VALID PF | TEST PF"
    )
    print("-" * 120)

    for candles in TIME_VALUES:

        tr = results[candles]["TRAIN"]
        va = results[candles]["VALIDATION"]
        te = results[candles]["TEST"]

        total = (
            tr["profit"] +
            va["profit"] +
            te["profit"]
        )

        print(
            f"{candles:4d} | "
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
