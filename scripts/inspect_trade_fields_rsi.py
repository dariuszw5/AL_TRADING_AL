from src.backtest.backtest_runner import BacktestRunner


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALIDATION": "data/backtest/BTCUSDT_1m_validation_5000.json",
    "TEST": "data/backtest/BTCUSDT_1m_test_5000.json",
}


def run(data_file, buy_rsi):
    runner = BacktestRunner(
        symbol="BTCUSDT",
        interval="1m",
        limit=5000,
        initial_balance=1000.0,
        buy_rsi=buy_rsi,
        sell_rsi=70.0,
        min_difference=1.0,
        trading_fee=0.0,
        rsi_method="classic",
        data_source="file",
        data_file=data_file,
    )

    runner.load_data()
    runner.run()

    return runner


def dump_trade_objects(runner, label):
    trades = runner.backtest_engine.get_trades()

    print()
    print("=" * 100)
    print(label)
    print("=" * 100)

    for i, trade in enumerate(trades, 1):
        print()
        print(f"TRADE #{i}")

        if hasattr(trade, "__dict__"):
            for key, value in vars(trade).items():
                print(f"  {key}: {value}")
        else:
            print(f"  TYPE: {type(trade)}")
            print(f"  VALUE: {trade}")


def main():
    for dataset_name, data_file in DATASETS.items():

        runner_3450 = run(data_file, 34.50)
        runner_3550 = run(data_file, 35.50)

        dump_trade_objects(
            runner_3450,
            f"{dataset_name} | RSI 34.50"
        )

        dump_trade_objects(
            runner_3550,
            f"{dataset_name} | RSI 35.50"
        )


if __name__ == "__main__":
    main()
