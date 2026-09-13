from src.backtest.backtest_runner import BacktestRunner


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALID": "data/backtest/BTCUSDT_1m_validation_5000.json",
    "TEST": "data/backtest/BTCUSDT_1m_test_5000.json",
}

STRATEGIES = {
    "BASELINE": {
        "buy": 34.5,
        "sell": 68.5,
        "time": 240,
    },
    "FINAL": {
        "buy": 33.8,
        "sell": 68.5,
        "time": 241,
    },
}

INITIAL_BALANCE = 1000.0
FEE = 0.0004


def run_backtest(data_path, params):
    runner = BacktestRunner(
        symbol="BTCUSDT",
        interval="1m",
        limit=5000,
        initial_balance=INITIAL_BALANCE,
        buy_rsi=params["buy"],
        sell_rsi=params["sell"],
        min_difference=1.0,
        trading_fee=FEE,
        rsi_method="classic",
        data_source="file",
        data_file=data_path,
    )

    runner.agent.config.max_position_candles = params["time"]

    runner.run()

    profit = runner.get_total_profit()

    return {
        "profit": profit,
        "final_balance": INITIAL_BALANCE + profit,
        "pf": runner.get_profit_factor(),
        "dd": runner.get_max_drawdown(),
        "wr": runner.get_win_rate(),
        "trades": runner.get_trade_count(),
    }


print()
print("=" * 125)
print("FINAL BENCHMARK | BASELINE vs FINAL")
print("=" * 125)

all_results = {}

for dataset_name, data_path in DATASETS.items():

    print()
    print("=" * 125)
    print(dataset_name)
    print("=" * 125)

    all_results[dataset_name] = {}

    for strategy_name, params in STRATEGIES.items():

        result = run_backtest(data_path, params)
        all_results[dataset_name][strategy_name] = result

        print()
        print(strategy_name)
        print(
            f"  BUY={params['buy']:.1f} | "
            f"SELL={params['sell']:.1f} | "
            f"TIME={params['time']}"
        )
        print(f"  Final balance : {result['final_balance']:>10.4f}")
        print(f"  Profit        : {result['profit']:>10.4f}")
        print(f"  PF            : {result['pf']:>10.4f}")
        print(f"  Drawdown      : {result['dd']:>10.4f}")
        print(f"  Win rate      : {result['wr']:>10.2f}%")
        print(f"  Trades        : {result['trades']:>10}")


print()
print("=" * 125)
print("FINAL - BASELINE DIFFERENCE")
print("=" * 125)

for dataset_name in DATASETS:

    base = all_results[dataset_name]["BASELINE"]
    final = all_results[dataset_name]["FINAL"]

    print()
    print(dataset_name)

    print(
        f"  Profit        : "
        f"{final['profit'] - base['profit']:+.4f}"
    )

    print(
        f"  PF            : "
        f"{final['pf'] - base['pf']:+.4f}"
    )

    print(
        f"  Drawdown      : "
        f"{final['dd'] - base['dd']:+.4f}"
    )

    print(
        f"  Win rate      : "
        f"{final['wr'] - base['wr']:+.2f} pp"
    )

    print(
        f"  Trades        : "
        f"{final['trades'] - base['trades']:+d}"
    )

    print(
        f"  Final balance : "
        f"{final['final_balance'] - base['final_balance']:+.4f}"
    )


print()
print("=" * 125)
print("TOTAL PROFIT")
print("=" * 125)

base_total = sum(
    all_results[name]["BASELINE"]["profit"]
    for name in DATASETS
)

final_total = sum(
    all_results[name]["FINAL"]["profit"]
    for name in DATASETS
)

print(f"BASELINE TOTAL = {base_total:+.4f}")
print(f"FINAL TOTAL    = {final_total:+.4f}")
print(f"IMPROVEMENT    = {final_total - base_total:+.4f}")

print()
print("=" * 125)
print("DONE")
print("=" * 125)
