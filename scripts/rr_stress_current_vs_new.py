from src.backtest.backtest_runner import BacktestRunner


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALID": "data/backtest/BTCUSDT_1m_validation_5000.json",
    "TEST": "data/backtest/BTCUSDT_1m_test_5000.json",
}

STRATEGIES = {
    "CURRENT_34.5_68.5_T240": {
        "buy_rsi": 34.5,
        "sell_rsi": 68.5,
        "time": 240,
    },
    "NEW_33.8_68.5_T241": {
        "buy_rsi": 33.8,
        "sell_rsi": 68.5,
        "time": 241,
    },
}

RR_VALUES = [1.5, 1.75, 2.0, 2.25, 2.5, 3.0]

FEE = 0.0004


def run_backtest(data_path, params, rr):
    runner = BacktestRunner(
        symbol="BTCUSDT",
        interval="1m",
        limit=5000,
        initial_balance=1000.0,
        buy_rsi=params["buy_rsi"],
        sell_rsi=params["sell_rsi"],
        min_difference=1.0,
        trading_fee=FEE,
        rsi_method="classic",
        risk_percent=5.0,
        max_daily_loss_percent=10.0,
        risk_reward_ratio=rr,
        data_source="file",
        data_file=data_path,
    )

    runner.agent.config.max_position_candles = params["time"]

    runner.run()

    return (
        runner.get_total_profit(),
        runner.get_profit_factor(),
        runner.get_max_drawdown(),
        runner.get_win_rate(),
        runner.get_trade_count(),
    )


for rr in RR_VALUES:
    print()
    print("=" * 95)
    print(f"RISK/REWARD = {rr:.2f} | FEE = {FEE:.4f}")
    print("=" * 95)

    for strategy_name, params in STRATEGIES.items():
        print()
        print(strategy_name)

        total_profit = 0.0

        for dataset_name, data_path in DATASETS.items():
            profit, pf, dd, wr, trades = run_backtest(
                data_path,
                params,
                rr,
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
