from src.backtest.backtest_runner import BacktestRunner


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALIDATION": "data/backtest/BTCUSDT_1m_validation_5000.json",
    "TEST": "data/backtest/BTCUSDT_1m_test_5000.json",
}


BUY_RSI = 35.50
SELL_VALUES = [69.0, 70.0, 76.5, 77.0, 78.0]


def run_backtest(path, sell_rsi):
    runner = BacktestRunner(
        symbol="BTCUSDT",
        interval="1m",
        limit=5000,
        initial_balance=1000.0,
        buy_rsi=BUY_RSI,
        sell_rsi=sell_rsi,
        min_difference=1.0,
        trading_fee=0.0,
        rsi_method="classic",
        data_source="file",
        data_file=path,
    )

    runner.load_data()
    runner.run()

    return runner


def trade_value(trade, *names):
    for name in names:
        if isinstance(trade, dict) and name in trade:
            return trade[name]

        if hasattr(trade, name):
            return getattr(trade, name)

    return None


def print_trade(index, trade):
    side = trade_value(
        trade,
        "side"
    )

    entry_index = trade_value(
        trade,
        "entry_index",
        "entry_candle_index",
        "entry_bar"
    )

    exit_index = trade_value(
        trade,
        "exit_index",
        "exit_candle_index",
        "exit_bar"
    )

    entry_price = trade_value(
        trade,
        "entry_price",
        "entry"
    )

    exit_price = trade_value(
        trade,
        "exit_price",
        "exit"
    )

    profit = trade_value(
        trade,
        "profit",
        "pnl",
        "profit_loss"
    )

    entry_timestamp = trade_value(
        trade,
        "entry_timestamp",
        "entry_time"
    )

    exit_timestamp = trade_value(
        trade,
        "exit_timestamp",
        "exit_time"
    )

    exit_reason = trade_value(
        trade,
        "exit_reason",
        "reason"
    )

    print(
        f"  #{index:02d} "
        f"SIDE={side:<4} "
        f"ENTRY={entry_index} "
        f"EXIT={exit_index} "
        f"ENTRY_PRICE={entry_price} "
        f"EXIT_PRICE={exit_price} "
        f"PROFIT={profit:+.4f} "
        f"REASON={exit_reason} "
        f"ENTRY_TS={entry_timestamp} "
        f"EXIT_TS={exit_timestamp}"
    )


def main():
    for dataset_name, path in DATASETS.items():

        print()
        print("#" * 140)
        print(f"{dataset_name} | SELL RSI SIDE COMPARISON")
        print("#" * 140)

        for sell_rsi in SELL_VALUES:

            runner = run_backtest(path, sell_rsi)
            engine = runner.backtest_engine

            print()
            print(
                f"SELL RSI={sell_rsi:.2f} | "
                f"TRADES={engine.get_trade_count()} | "
                f"PROFIT={engine.get_total_profit():+.4f} | "
                f"PF={engine.get_profit_factor():.4f} | "
                f"DD={engine.get_max_drawdown():.4f}"
            )

            trades = engine.get_trades()

            if not trades:
                print("  [NO TRADES]")
                continue

            buy_count = sum(
                1
                for trade in trades
                if trade_value(trade, "side") == "BUY"
            )

            sell_count = sum(
                1
                for trade in trades
                if trade_value(trade, "side") == "SELL"
            )

            print(
                f"  BUY TRADES={buy_count} | "
                f"SELL TRADES={sell_count}"
            )

            for i, trade in enumerate(trades, start=1):
                print_trade(i, trade)


if __name__ == "__main__":
    main()
