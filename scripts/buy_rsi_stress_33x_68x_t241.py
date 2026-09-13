from src.backtest.backtest_runner import BacktestRunner


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALID": "data/backtest/BTCUSDT_1m_validation_5000.json",
    "TEST": "data/backtest/BTCUSDT_1m_test_5000.json",
}

BUY_VALUES = [33.4, 33.5, 33.6, 33.7, 33.8, 33.9, 34.0, 34.1, 34.2]

SELL_RSI = 68.5
MAX_TIME = 241
FEE = 0.0004


def run_backtest(data_path, buy_rsi):
    runner = BacktestRunner(
        symbol="BTCUSDT",
        interval="1m",
        limit=5000,
        initial_balance=1000.0,
        buy_rsi=buy_rsi,
        sell_rsi=SELL_RSI,
        min_difference=1.0,
        trading_fee=FEE,
        rsi_method="classic",
        data_source="file",
        data_file=data_path,
    )

    runner.agent.config.max_position_candles = MAX_TIME

    runner.run()

    return (
        runner.get_total_profit(),
        runner.get_profit_factor(),
        runner.get_max_drawdown(),
        runner.get_win_rate(),
        runner.get_trade_count(),
    )


print()
print("=" * 95)
print(
    f"BUY RSI STRESS | SELL={SELL_RSI} | TIME={MAX_TIME} | FEE={FEE:.4f}"
)
print("=" * 95)

for buy_rsi in BUY_VALUES:
    print()
    print(f"BUY RSI = {buy_rsi:.1f}")

    total_profit = 0.0

    for dataset_name, data_path in DATASETS.items():
        profit, pf, dd, wr, trades = run_backtest(
            data_path,
            buy_rsi,
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
