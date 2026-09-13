import json

from src.backtest.backtest_runner import BacktestRunner


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALIDATION": "data/backtest/BTCUSDT_1m_validation_5000.json",
    "TEST": "data/backtest/BTCUSDT_1m_test_5000.json",
}

BUY_RSI = 35.50
SELL_VALUES = [69.0, 77.0]


def load_candles(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


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


def timestamp_to_index(candles):
    result = {}

    for index, candle in enumerate(candles):
        if isinstance(candle, dict):
            timestamp = candle.get("timestamp")
        else:
            timestamp = candle.timestamp

        result[timestamp] = index

    return result


def print_trade(index, trade, ts_index):
    side = trade_value(trade, "side")

    entry_timestamp = trade_value(
        trade,
        "entry_timestamp",
        "entry_time",
    )

    exit_timestamp = trade_value(
        trade,
        "exit_timestamp",
        "exit_time",
    )

    entry_index = ts_index.get(entry_timestamp)
    exit_index = ts_index.get(exit_timestamp)

    entry_price = trade_value(
        trade,
        "entry_price",
        "entry",
    )

    exit_price = trade_value(
        trade,
        "exit_price",
        "exit",
    )

    profit = trade_value(
        trade,
        "profit",
        "pnl",
        "profit_loss",
    )

    reason = trade_value(
        trade,
        "exit_reason",
        "reason",
    )

    print(
        f"  #{index:02d} "
        f"SIDE={side:<4} "
        f"ENTRY_INDEX={entry_index} "
        f"EXIT_INDEX={exit_index} "
        f"ENTRY_PRICE={entry_price} "
        f"EXIT_PRICE={exit_price} "
        f"PROFIT={profit:+.4f} "
        f"REASON={reason}"
    )


def main():
    for dataset_name, path in DATASETS.items():

        print()
        print("=" * 140)
        print(f"{dataset_name} | SELL 69.00 vs SELL 77.00 | TRADE INDEX MAPPING")
        print("=" * 140)

        candles = load_candles(path)
        ts_index = timestamp_to_index(candles)

        for sell_rsi in SELL_VALUES:

            runner = run_backtest(path, sell_rsi)
            engine = runner.backtest_engine
            trades = engine.get_trades()

            print()
            print(
                f"SELL RSI={sell_rsi:.2f} | "
                f"TRADES={engine.get_trade_count()} | "
                f"PROFIT={engine.get_total_profit():+.4f} | "
                f"PF={engine.get_profit_factor():.4f} | "
                f"DD={engine.get_max_drawdown():.4f}"
            )

            for i, trade in enumerate(trades, start=1):
                print_trade(i, trade, ts_index)


if __name__ == "__main__":
    main()
