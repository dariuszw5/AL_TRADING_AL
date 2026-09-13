from src.backtest.backtest_runner import BacktestRunner


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALIDATION": "data/backtest/BTCUSDT_1m_validation_5000.json",
    "TEST": "data/backtest/BTCUSDT_1m_test_5000.json",
    "OOS #1": "data/backtest/BTCUSDT_1m_forward_5000.json",
    "OOS #2": "data/backtest/BTCUSDT_1m_forward_5000_oos2.json",
}


FEES = [
    0.0004,
    0.0005,
    0.0006,
    0.0008,
    0.0010,
]


print()
print("=" * 125)
print("=== FROZEN STRATEGY | FEE STRESS TEST ===")
print("=" * 125)
print("BUY=33.8 | SELL=68.5 | TIME=241 | RSI=classic | MIN_DIFF=1.0")
print("Strategia zamrożona — zmieniamy WYŁĄCZNIE koszt transakcyjny.")
print()


for fee in FEES:

    print()
    print("=" * 125)
    print(f"FEE = {fee:.4f}")
    print("=" * 125)

    print(
        f"{'DATASET':<12} | "
        f"{'TRADES':>6} | "
        f"{'W/L':>7} | "
        f"{'WR':>7} | "
        f"{'PROFIT':>11} | "
        f"{'PF':>8} | "
        f"{'EXPECT.':>10} | "
        f"{'FINAL':>11}"
    )

    print("-" * 125)

    for name, data_file in DATASETS.items():

        runner = BacktestRunner(
            symbol="BTCUSDT",
            interval="1m",
            limit=5000,
            initial_balance=1000.0,
            buy_rsi=33.8,
            sell_rsi=68.5,
            min_difference=1.0,
            trading_fee=fee,
            rsi_method="classic",
            data_source="file",
            data_file=data_file,
        )

        runner.agent.config.max_position_candles = 241

        runner.load_data()
        runner.run()

        summary = runner.get_summary()

        wins = int(summary["winning_trades"])
        losses = int(summary["losing_trades"])

        print(
            f"{name:<12} | "
            f"{int(summary['trades']):>6} | "
            f"{wins}/{losses:>5} | "
            f"{float(summary['win_rate']):>6.2f}% | "
            f"{float(summary['total_profit']):>11.4f} | "
            f"{float(summary['profit_factor']):>8.4f} | "
            f"{float(summary['expectancy']):>10.4f} | "
            f"{float(summary['final_balance']):>11.4f}"
        )


print()
print("=" * 125)
print("END")
print("=" * 125)
