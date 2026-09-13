from src.backtest.backtest_runner import BacktestRunner


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALID": "data/backtest/BTCUSDT_1m_validation_5000.json",
    "TEST": "data/backtest/BTCUSDT_1m_test_5000.json",
}

STRATEGIES = {
    "BASELINE_34.5_68.5_T240": {
        "buy": 34.5,
        "sell": 68.5,
        "time": 240,
    },
    "FINAL_33.8_68.5_T241": {
        "buy": 33.8,
        "sell": 68.5,
        "time": 241,
    },
}

FEES = [
    0.0004,
    0.0005,
    0.0006,
    0.0007,
    0.0008,
    0.0009,
    0.0010,
    0.0012,
]


def run_backtest(data_path, buy_rsi, sell_rsi, max_time, fee):
    runner = BacktestRunner(
        symbol="BTCUSDT",
        interval="1m",
        limit=5000,
        initial_balance=1000.0,
        buy_rsi=buy_rsi,
        sell_rsi=sell_rsi,
        min_difference=1.0,
        trading_fee=fee,
        rsi_method="classic",
        data_source="file",
        data_file=data_path,
    )

    runner.agent.config.max_position_candles = max_time

    runner.run()

    return (
        runner.get_total_profit(),
        runner.get_profit_factor(),
        runner.get_max_drawdown(),
        runner.get_win_rate(),
        runner.get_trade_count(),
    )


print()
print("=" * 125)
print("FINAL FEE ROBUSTNESS | BASELINE vs FINAL CANDIDATE")
print("=" * 125)

for fee in FEES:
    print()
    print(f"FEE = {fee:.4f} ({fee * 100:.2f}%)")
    print("-" * 125)

    for strategy_name, params in STRATEGIES.items():

        total_profit = 0.0

        print(strategy_name)

        for dataset_name, data_path in DATASETS.items():

            profit, pf, dd, wr, trades = run_backtest(
                data_path,
                params["buy"],
                params["sell"],
                params["time"],
                fee,
            )

            total_profit += profit

            print(
                f"  {dataset_name:<5} | "
                f"Profit={profit:>9.4f} | "
                f"PF={pf:>7.4f} | "
                f"DD={dd:>8.4f} | "
                f"WR={wr:>6.2f}% | "
                f"Trades={trades:>3}"
            )

        print(f"  TOTAL | Profit={total_profit:>9.4f}")

print()
print("=" * 125)
print("DONE")
print("=" * 125)
