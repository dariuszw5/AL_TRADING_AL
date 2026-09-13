from src.backtest.backtest_runner import BacktestRunner


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALIDATION": "data/backtest/BTCUSDT_1m_validation_5000.json",
    "TEST": "data/backtest/BTCUSDT_1m_test_5000.json",
}


BUY_VALUES = [33.8, 33.9, 34.0, 34.1]

SELL_VALUES = [68.5, 68.6, 68.7, 68.8]

TIME_VALUES = [238, 239, 240, 241, 242]


MIN_DIFF = 1.0


def run_test(path, buy_rsi, sell_rsi, max_position_candles):

    runner = BacktestRunner(
        symbol="BTCUSDT",
        interval="1m",
        limit=5000,
        initial_balance=1000.0,
        buy_rsi=buy_rsi,
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

    print("=" * 135)
    print("=== BUY x SELL x TIME EXIT INTERACTION ===")
    print("=== MIN_DIFF=1.00 | CLASSIC | FEE=0.0004 | SL=5% | RR=2 ===")
    print("=" * 135)

    results = {}

    total_tests = (
        len(BUY_VALUES)
        * len(SELL_VALUES)
        * len(TIME_VALUES)
        * len(DATASETS)
    )

    completed = 0

    print(f"=== COMBINATIONS: "
          f"{len(BUY_VALUES)} BUY x "
          f"{len(SELL_VALUES)} SELL x "
          f"{len(TIME_VALUES)} TIME = "
          f"{len(BUY_VALUES) * len(SELL_VALUES) * len(TIME_VALUES)} ===")

    print(f"=== FULL BACKTESTS: {total_tests} ===")
    print("=" * 135)

    for buy in BUY_VALUES:

        results[buy] = {}

        for sell in SELL_VALUES:

            results[buy][sell] = {}

            for candles in TIME_VALUES:

                results[buy][sell][candles] = {}

                for name, path in DATASETS.items():

                    results[buy][sell][candles][name] = run_test(
                        path,
                        buy,
                        sell,
                        candles
                    )

                    completed += 1

                tr = results[buy][sell][candles]["TRAIN"]
                va = results[buy][sell][candles]["VALIDATION"]
                te = results[buy][sell][candles]["TEST"]

                total = (
                    tr["profit"]
                    + va["profit"]
                    + te["profit"]
                )

                print(
                    f"BUY={buy:4.1f} "
                    f"SELL={sell:4.1f} "
                    f"TIME={candles:3d} | "
                    f"TR={tr['profit']:8.4f} "
                    f"VA={va['profit']:8.4f} "
                    f"TE={te['profit']:8.4f} | "
                    f"TOTAL={total:9.4f} | "
                    f"PF={tr['pf']:.3f}/"
                    f"{va['pf']:.3f}/"
                    f"{te['pf']:.3f} | "
                    f"{completed}/{total_tests}"
                )

    ranking = []

    for buy in BUY_VALUES:
        for sell in SELL_VALUES:
            for candles in TIME_VALUES:

                tr = results[buy][sell][candles]["TRAIN"]
                va = results[buy][sell][candles]["VALIDATION"]
                te = results[buy][sell][candles]["TEST"]

                total = (
                    tr["profit"]
                    + va["profit"]
                    + te["profit"]
                )

                ranking.append({
                    "buy": buy,
                    "sell": sell,
                    "time": candles,
                    "train": tr,
                    "valid": va,
                    "test": te,
                    "total": total,
                })

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

    print("\n" + "=" * 135)
    print("=== ROBUST CANDIDATES ===")
    print("=== ALL 3 DATASETS PROFITABLE + PF > 1 ===")
    print("=" * 135)

    print(
        "RANK | BUY SELL TIME | TOTAL PROF | "
        "TRAIN | VALID | TEST | "
        "TRAIN PF | VALID PF | TEST PF"
    )
    print("-" * 135)

    for i, x in enumerate(robust[:30], 1):

        print(
            f"{i:4d} | "
            f"{x['buy']:4.1f} "
            f"{x['sell']:4.1f} "
            f"{x['time']:4d} | "
            f"{x['total']:10.4f} | "
            f"{x['train']['profit']:7.2f} | "
            f"{x['valid']['profit']:7.2f} | "
            f"{x['test']['profit']:7.2f} | "
            f"{x['train']['pf']:8.4f} | "
            f"{x['valid']['pf']:8.4f} | "
            f"{x['test']['pf']:8.4f}"
        )

    print("\n" + "=" * 135)
    print("=== TOP 20 BY TOTAL PROFIT ===")
    print("=" * 135)

    ranking.sort(key=lambda x: x["total"], reverse=True)

    for i, x in enumerate(ranking[:20], 1):

        print(
            f"{i:2d}. "
            f"BUY={x['buy']:4.1f} "
            f"SELL={x['sell']:4.1f} "
            f"TIME={x['time']:3d} | "
            f"TOTAL={x['total']:9.4f} | "
            f"TRAIN={x['train']['profit']:8.4f} | "
            f"VALID={x['valid']['profit']:8.4f} | "
            f"TEST={x['test']['profit']:8.4f}"
        )

    print("\n" + "=" * 135)
    print("=== CURRENT FROZEN CANDIDATE ===")
    print("=== BUY=34.5 | SELL=68.5 | TIME=240 ===")
    print("=== This candidate is outside the local BUY grid but remains the baseline ===")
    print("=" * 135)


if __name__ == "__main__":
    main()
