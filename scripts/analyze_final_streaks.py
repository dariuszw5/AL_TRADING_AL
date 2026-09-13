from src.backtest.backtest_runner import BacktestRunner


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALIDATION": "data/backtest/BTCUSDT_1m_validation_5000.json",
    "TEST": "data/backtest/BTCUSDT_1m_test_5000.json",
}


def run_backtest(data_file):
    runner = BacktestRunner(
        symbol="BTCUSDT",
        interval="1m",
        limit=5000,
        initial_balance=1000.0,
        buy_rsi=34.50,
        sell_rsi=68.50,
        min_difference=1.0,
        trading_fee=0.0004,
        rsi_method="classic",
        data_source="file",
        data_file=data_file,
    )

    runner.agent.config.stop_loss_percent = 5.0
    runner.agent.config.risk_reward_ratio = 2.0
    runner.agent.config.max_position_candles = 240

    runner.load_data()
    runner.run()

    return runner


for dataset_name, data_file in DATASETS.items():

    runner = run_backtest(data_file)
    trades = runner.get_trades()

    current_loss_streak = 0
    max_loss_streak = 0
    current_win_streak = 0
    max_win_streak = 0

    worst_trade = None
    best_trade = None

    print()
    print("=" * 90)
    print(f"=== {dataset_name} STREAK ANALYSIS ===")
    print("=" * 90)

    for i, trade in enumerate(trades, 1):

        profit = float(trade.get("profit", 0.0))

        if best_trade is None or profit > best_trade[0]:
            best_trade = (profit, i, trade)

        if worst_trade is None or profit < worst_trade[0]:
            worst_trade = (profit, i, trade)

        if profit < 0:
            current_loss_streak += 1
            current_win_streak = 0
            max_loss_streak = max(max_loss_streak, current_loss_streak)

        elif profit > 0:
            current_win_streak += 1
            current_loss_streak = 0
            max_win_streak = max(max_win_streak, current_win_streak)

        else:
            current_loss_streak = 0
            current_win_streak = 0

    print(f"Trades              : {len(trades)}")
    print(f"Total profit        : {runner.get_total_profit():10.4f}")
    print(f"Profit factor       : {runner.get_profit_factor():10.4f}")
    print(f"Expectancy          : {runner.get_expectancy():10.4f}")
    print(f"Max winning streak  : {max_win_streak}")
    print(f"Max losing streak   : {max_loss_streak}")

    if best_trade:
        print()
        print(
            f"Best trade          : #{best_trade[1]} "
            f"profit={best_trade[0]:.4f}"
        )

    if worst_trade:
        print(
            f"Worst trade         : #{worst_trade[1]} "
            f"profit={worst_trade[0]:.4f}"
        )

    print()
    print("TRADE RESULTS")
    print("-" * 90)

    for i, trade in enumerate(trades, 1):
        profit = float(trade.get("profit", 0.0))
        reason = trade.get("exit_reason", "?")

        print(
            f"{i:>3} | "
            f"profit={profit:>10.4f} | "
            f"reason={reason}"
        )

    print()
