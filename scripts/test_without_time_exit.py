from src.backtest.backtest_runner import BacktestRunner


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALIDATION": "data/backtest/BTCUSDT_1m_validation_5000.json",
}


def run_test(data_file):
    runner = BacktestRunner(
        symbol="BTCUSDT",
        interval="1m",
        limit=5000,
        initial_balance=1000.0,
        buy_rsi=30.0,
        sell_rsi=70.0,
        min_difference=1.0,
        trading_fee=0.0,
        rsi_method="classic",
        data_source="file",
        data_file=data_file,
    )

    # Praktycznie wyłączamy TIME_EXIT.
    # 10000 minut > długość naszego zbioru danych.
    runner.agent.config.max_position_candles = 10000

    runner.load_data()
    runner.run()

    return runner


for name, data_file in DATASETS.items():

    runner = run_test(data_file)

    trades = runner.get_trades()

    exit_reasons = {}

    for trade in trades:
        reason = trade.get("exit_reason", "UNKNOWN")
        exit_reasons[reason] = exit_reasons.get(reason, 0) + 1

    print()
    print(f"=== {name} WITHOUT TIME EXIT ===")
    print()

    print(f"TRADES:      {runner.get_trade_count()}")
    print(f"WIN RATE:    {runner.get_win_rate():.2f}%")
    print(f"PROFIT:      {runner.get_total_profit():.4f}")
    print(f"PF:          {runner.get_profit_factor():.4f}")
    print(f"DRAWDOWN:    {runner.get_max_drawdown():.4f}")
    print(f"EXPECTANCY:  {runner.get_expectancy():.4f}")

    print()
    print("EXIT REASONS:")

    for reason, count in sorted(exit_reasons.items()):
        print(f"  {reason}: {count}")

    print()