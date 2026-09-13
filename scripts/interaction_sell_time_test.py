from src.backtest.backtest_runner import BacktestRunner


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALIDATION": "data/backtest/BTCUSDT_1m_validation_5000.json",
    "TEST": "data/backtest/BTCUSDT_1m_test_5000.json",
}

BUY_RSI = 34.5

SELL_VALUES = [
    68.2, 68.3, 68.4, 68.5, 68.6,
    68.7, 68.8, 68.9, 69.0
]

TIME_VALUES = [238, 239, 240, 241, 242]

MIN_DIFF = 1.0


def run_test(path, sell_rsi, max_position_candles):

    runner = BacktestRunner(
        symbol="BTCUSDT",
        interval="1m",
        limit=5000,
        initial_balance=1000.0,
        buy_rsi=BUY_RSI,
        sell_rsi=sell_rsi,
        min_difference=MIN_DIFF,
        trading_fee=0.0004,
        rsi_method="classic",
        risk_percent=5.0,
        max_daily_loss_percent=10.0,
        risk_reward_ratio=2.0,
        data_source="file",
        data_file=path,
    )

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

    print("=" * 125)
    print("=== SELL RSI x TIME EXIT INTERACTION ===")
    print("=== BUY=34.50 | MIN_DIFF=1.00 | CLASSIC | FEE=0.0004 ===")
    print("=" * 125)

    results = {}

    for sell in SELL_VALUES:

        results[sell] = {}

        for candles in TIME_VALUES:

            results[sell][candles] = {}

            for name, path in DATASETS.items():

                results[sell][candles][name] = run_test(
                    path,
                    sell,
                    candles
                )

    print("\n" + "=" * 125)
    print("=== ALL COMBINATIONS ===")
    print("=" * 125)

    print(
        "SELL  TIME | TRAIN PROF | VALID PROF | TEST PROF | "
        "TOTAL PROF | TRAIN PF | VALID PF | TEST PF"
    )
    print("-" * 125)

    ranking = []

    for sell in SELL_VALUES:

        for candles in TIME_VALUES:

            tr = results[sell][candles]["TRAIN"]
            va = results[sell][candles]["VALIDATION"]
            te = results[sell][candles]["TEST"]

            total = (
                tr["profit"] +
                va["profit"] +
                te["profit"]
            )

            item = {
                "sell": sell,
                "time": candles,
                "train": tr,
                "valid": va,
                "test": te,
                "total": total,
            }

            ranking.append(item)

            print(
                f"{sell:4.1f} {candles:4d} | "
                f"{tr['profit']:10.4f} | "
                f"{va['profit']:11.4f} | "
                f"{te['profit']:9.4f} | "
                f"{total:10.4f} | "
                f"{tr['pf']:8.4f} | "
                f"{va['pf']:8.4f} | "
                f"{te['pf']:7.4f}"
            )

    robust = [
        x for x in ranking
        if (
            x["train"]["profit"] > 0
            and x["valid"]["profit"] > 0
            and x["test"]["profit"] > 0
            and x["train"]["pf"] > 1
            and x["valid"]["pf"] > 1
            and x["test"]["pf"] > 1
        )
    ]

    robust.sort(key=lambda x: x["total"], reverse=True)

    print("\n" + "=" * 125)
    print("=== ROBUST CANDIDATES ===")
    print("=" * 125)

    print(
        "RANK | SELL  TIME | TOTAL PROF | "
        "TRAIN | VALID | TEST | TRAIN PF | VALID PF | TEST PF"
    )
    print("-" * 125)

    for i, x in enumerate(robust, 1):

        print(
            f"{i:4d} | "
            f"{x['sell']:4.1f} {x['time']:4d} | "
            f"{x['total']:10.4f} | "
            f"{x['train']['profit']:6.2f} | "
            f"{x['valid']['profit']:6.2f} | "
            f"{x['test']['profit']:6.2f} | "
            f"{x['train']['pf']:8.4f} | "
            f"{x['valid']['pf']:8.4f} | "
            f"{x['test']['pf']:7.4f}"
        )

    ranking.sort(key=lambda x: x["total"], reverse=True)

    print("\n" + "=" * 125)
    print("=== TOP 15 BY TOTAL PROFIT ===")
    print("=" * 125)

    for i, x in enumerate(ranking[:15], 1):

        print(
            f"{i:2d}. SELL={x['sell']:4.1f} | "
            f"TIME={x['time']:3d} | "
            f"TOTAL={x['total']:9.4f} | "
            f"TRAIN={x['train']['profit']:8.4f} | "
            f"VALID={x['valid']['profit']:8.4f} | "
            f"TEST={x['test']['profit']:8.4f}"
        )


if __name__ == "__main__":
    main()
