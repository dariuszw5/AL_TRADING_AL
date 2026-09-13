from src.data.data_provider import DataProvider
from src.backtest.backtest_runner import BacktestRunner


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALIDATION": "data/backtest/BTCUSDT_1m_validation_5000.json",
}


RSI_A = 34.50
RSI_B = 35.50


def run_backtest(path, buy_rsi):
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
        data_file=path,
    )

    runner.load_data()
    runner.run()

    return runner


def get_index_from_timestamp(data, timestamp):
    for i, candle in enumerate(data):
        if candle.timestamp == timestamp:
            return i

    return None


def get_trade_profit(trade):
    possible_keys = [
        "profit",
        "pnl",
        "profit_loss",
        "realized_profit",
        "net_profit",
    ]

    for key in possible_keys:
        value = trade.get(key)

        if value is not None:
            return float(value)

    return None


def print_trade_details(
    label,
    number,
    trade,
    data
):
    entry_timestamp = trade.get("entry_timestamp")
    exit_timestamp = trade.get("exit_timestamp")

    entry_index = get_index_from_timestamp(
        data,
        entry_timestamp
    )

    exit_index = get_index_from_timestamp(
        data,
        exit_timestamp
    )

    entry_price = trade.get("entry_price")
    exit_price = trade.get("exit_price")

    profit = get_trade_profit(trade)

    print(
        f"{label} #{number:2d} | "
        f"ENTRY_INDEX={str(entry_index):>4} | "
        f"EXIT_INDEX={str(exit_index):>4} | "
        f"ENTRY_PRICE={str(entry_price):>10} | "
        f"EXIT_PRICE={str(exit_price):>10} | "
        f"PROFIT={str(profit):>10}"
    )


def compare_trades(
    trades_a,
    trades_b,
    data
):
    max_count = max(
        len(trades_a),
        len(trades_b)
    )

    print()
    print("=" * 150)
    print("TRADE-BY-TRADE COMPARISON")
    print("=" * 150)

    total_a = 0.0
    total_b = 0.0

    for i in range(max_count):

        trade_a = (
            trades_a[i]
            if i < len(trades_a)
            else None
        )

        trade_b = (
            trades_b[i]
            if i < len(trades_b)
            else None
        )

        print()
        print("-" * 150)
        print(f"TRADE SLOT #{i + 1}")

        profit_a = None
        profit_b = None

        if trade_a is not None:
            entry_a = get_index_from_timestamp(
                data,
                trade_a.get("entry_timestamp")
            )

            exit_a = get_index_from_timestamp(
                data,
                trade_a.get("exit_timestamp")
            )

            profit_a = get_trade_profit(trade_a)

            print(
                f"34.50 | "
                f"ENTRY={str(entry_a):>4} | "
                f"EXIT={str(exit_a):>4} | "
                f"ENTRY_PRICE={str(trade_a.get('entry_price')):>10} | "
                f"EXIT_PRICE={str(trade_a.get('exit_price')):>10} | "
                f"PROFIT={str(profit_a):>10}"
            )

        else:
            print("34.50 | NO TRADE")

        if trade_b is not None:
            entry_b = get_index_from_timestamp(
                data,
                trade_b.get("entry_timestamp")
            )

            exit_b = get_index_from_timestamp(
                data,
                trade_b.get("exit_timestamp")
            )

            profit_b = get_trade_profit(trade_b)

            print(
                f"35.50 | "
                f"ENTRY={str(entry_b):>4} | "
                f"EXIT={str(exit_b):>4} | "
                f"ENTRY_PRICE={str(trade_b.get('entry_price')):>10} | "
                f"EXIT_PRICE={str(trade_b.get('exit_price')):>10} | "
                f"PROFIT={str(profit_b):>10}"
            )

        else:
            print("35.50 | NO TRADE")

        if profit_a is not None:
            total_a += profit_a

        if profit_b is not None:
            total_b += profit_b

        if (
            profit_a is not None
            and profit_b is not None
        ):
            difference = profit_b - profit_a

            print(
                f"DIFFERENCE 35.50 - 34.50 = "
                f"{difference:+.4f}"
            )

        elif (
            profit_a is None
            and profit_b is not None
        ):
            print(
                f"NEW TRADE WITH 35.50 = "
                f"{profit_b:+.4f}"
            )

        elif (
            profit_a is not None
            and profit_b is None
        ):
            print(
                f"TRADE MISSING WITH 35.50 = "
                f"{-profit_a:+.4f}"
            )

    print()
    print("=" * 150)
    print("CALCULATED TRADE PROFIT TOTAL")
    print("=" * 150)
    print(
        f"34.50 = {total_a:+.4f}"
    )
    print(
        f"35.50 = {total_b:+.4f}"
    )
    print(
        f"DIFFERENCE = {total_b - total_a:+.4f}"
    )


def print_summary(
    label,
    runner
):
    engine = runner.backtest_engine

    print()
    print(
        f"{label} | "
        f"TRADES={engine.get_trade_count()} | "
        f"PROFIT={engine.get_total_profit():+.4f} | "
        f"PF={engine.get_profit_factor():.4f} | "
        f"DD={engine.get_max_drawdown():.4f}"
    )


def main():
    provider = DataProvider()

    for dataset_name, path in DATASETS.items():

        print()
        print("#" * 150)
        print(
            f"{dataset_name} | "
            f"TRADE-BY-TRADE: RSI 34.50 vs 35.50"
        )
        print("#" * 150)

        data = provider.load_candles(path)

        runner_a = run_backtest(
            path,
            RSI_A
        )

        runner_b = run_backtest(
            path,
            RSI_B
        )

        trades_a = (
            runner_a.backtest_engine.get_trades()
        )

        trades_b = (
            runner_b.backtest_engine.get_trades()
        )

        print_summary(
            "34.50",
            runner_a
        )

        print_summary(
            "35.50",
            runner_b
        )

        compare_trades(
            trades_a,
            trades_b,
            data
        )

        print()
        print("=" * 150)
        print("RAW TRADE DICTIONARIES")
        print("=" * 150)

        print()
        print("34.50 FIRST TRADE:")
        if trades_a:
            print(trades_a[0])

        print()
        print("35.50 FIRST TRADE:")
        if trades_b:
            print(trades_b[0])


if __name__ == "__main__":
    main()
