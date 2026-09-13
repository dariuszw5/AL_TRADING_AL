from src.data.data_provider import DataProvider
from src.backtest.backtest_runner import BacktestRunner
from src.analysis.indicators import sma, ema, rsi


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALIDATION": "data/backtest/BTCUSDT_1m_validation_5000.json",
    "TEST": "data/backtest/BTCUSDT_1m_test_5000.json",
}


BASE_RSI = 34.50
NEW_RSI = 35.50


def get_index_from_timestamp(data, timestamp):
    for i, candle in enumerate(data):
        if candle.timestamp == timestamp:
            return i

    return None


def calculate_indicators(data):
    closes = [c.close for c in data]

    sma_values = sma(closes, 20)
    ema_values = ema(closes, 20)
    rsi_values = rsi(closes, 14)

    return sma_values, ema_values, rsi_values


def get_values_at_index(
    sma_values,
    ema_values,
    rsi_values,
    index
):
    sma_index = index - 19
    ema_index = index - 19
    rsi_index = index - 14

    if sma_index < 0:
        return None

    if ema_index < 0:
        return None

    if rsi_index < 0:
        return None

    if sma_index >= len(sma_values):
        return None

    if ema_index >= len(ema_values):
        return None

    if rsi_index >= len(rsi_values):
        return None

    return (
        sma_values[sma_index],
        ema_values[ema_index],
        rsi_values[rsi_index]
    )


def is_buy_signal(
    sma_value,
    ema_value,
    rsi_value,
    buy_rsi
):
    difference = abs(
        ema_value - sma_value
    )

    return (
        ema_value > sma_value
        and rsi_value < buy_rsi
        and difference >= 1.0
    )


def get_trade_ranges(runner, data):
    trades = runner.backtest_engine.get_trades()

    ranges = []

    for number, trade in enumerate(
        trades,
        start=1
    ):
        if not isinstance(trade, dict):
            continue

        entry_timestamp = trade.get(
            "entry_timestamp"
        )

        exit_timestamp = trade.get(
            "exit_timestamp"
        )

        entry_index = None
        exit_index = None

        if entry_timestamp is not None:
            entry_index = get_index_from_timestamp(
                data,
                entry_timestamp
            )

        if exit_timestamp is not None:
            exit_index = get_index_from_timestamp(
                data,
                exit_timestamp
            )

        ranges.append({
            "number": number,
            "entry_index": entry_index,
            "exit_index": exit_index,
            "entry_timestamp": entry_timestamp,
            "exit_timestamp": exit_timestamp,
            "trade": trade,
        })

    return ranges


def find_containing_trade(
    trade_ranges,
    index
):
    for trade in trade_ranges:

        entry_index = trade["entry_index"]
        exit_index = trade["exit_index"]

        if entry_index is None:
            continue

        if exit_index is None:
            if index >= entry_index:
                return trade

        elif entry_index <= index <= exit_index:
            return trade

    return None


def main():
    provider = DataProvider()

    for dataset_name, path in DATASETS.items():

        print()
        print("#" * 150)
        print(
            f"{dataset_name} | "
            f"FULL SCAN: NEW BUY SIGNALS 34.50 -> 35.50"
        )
        print("#" * 150)

        data = provider.load_candles(path)

        sma_values, ema_values, rsi_values = (
            calculate_indicators(data)
        )

        runner_3450 = BacktestRunner(
            symbol="BTCUSDT",
            interval="1m",
            limit=5000,
            initial_balance=1000.0,
            buy_rsi=BASE_RSI,
            sell_rsi=70.0,
            min_difference=1.0,
            trading_fee=0.0,
            rsi_method="classic",
            data_source="file",
            data_file=path,
        )

        runner_3450.load_data()
        runner_3450.run()

        ranges_3450 = get_trade_ranges(
            runner_3450,
            data
        )

        runner_3550 = BacktestRunner(
            symbol="BTCUSDT",
            interval="1m",
            limit=5000,
            initial_balance=1000.0,
            buy_rsi=NEW_RSI,
            sell_rsi=70.0,
            min_difference=1.0,
            trading_fee=0.0,
            rsi_method="classic",
            data_source="file",
            data_file=path,
        )

        runner_3550.load_data()
        runner_3550.run()

        ranges_3550 = get_trade_ranges(
            runner_3550,
            data
        )

        new_signals = []

        for i in range(len(data)):

            values = get_values_at_index(
                sma_values,
                ema_values,
                rsi_values,
                i
            )

            if values is None:
                continue

            sma_value, ema_value, rsi_value = values

            buy_3450 = is_buy_signal(
                sma_value,
                ema_value,
                rsi_value,
                BASE_RSI
            )

            buy_3550 = is_buy_signal(
                sma_value,
                ema_value,
                rsi_value,
                NEW_RSI
            )

            if buy_3550 and not buy_3450:

                trade_3450 = find_containing_trade(
                    ranges_3450,
                    i
                )

                trade_3550 = find_containing_trade(
                    ranges_3550,
                    i
                )

                new_signals.append({
                    "index": i,
                    "timestamp": data[i].timestamp,
                    "price": data[i].close,
                    "rsi": rsi_value,
                    "difference": abs(
                        ema_value - sma_value
                    ),
                    "trade_3450": trade_3450,
                    "trade_3550": trade_3550,
                })

        print()
        print(
            f"TOTAL NEW 35.50 SIGNALS = "
            f"{len(new_signals)}"
        )

        if not new_signals:
            print(
                "NO NEW 35.50 SIGNALS "
                "RELATIVE TO 34.50"
            )
            continue

        print()
        print("-" * 150)

        for item in new_signals:

            trade_3450 = item["trade_3450"]
            trade_3550 = item["trade_3550"]

            if trade_3450 is None:
                position_3450 = "NONE"
            else:
                position_3450 = (
                    f"TRADE #{trade_3450['number']} "
                    f"[{trade_3450['entry_index']}"
                    f"-"
                    f"{trade_3450['exit_index']}]"
                )

            if trade_3550 is None:
                position_3550 = "NONE"
            else:
                position_3550 = (
                    f"TRADE #{trade_3550['number']} "
                    f"[{trade_3550['entry_index']}"
                    f"-"
                    f"{trade_3550['exit_index']}]"
                )

            print(
                f"INDEX={item['index']:4d} | "
                f"TS={item['timestamp']} | "
                f"PRICE={item['price']:10.2f} | "
                f"RSI={item['rsi']:7.3f} | "
                f"EMA-SMA={item['difference']:7.3f} | "
                f"34.50={position_3450} | "
                f"35.50={position_3550}"
            )

        print("-" * 150)

        print()
        print("BACKTEST SUMMARY")
        print()

        print(
            f"34.50 | "
            f"TRADES={runner_3450.backtest_engine.get_trade_count():2d} | "
            f"PROFIT={runner_3450.backtest_engine.get_total_profit():10.4f} | "
            f"PF={runner_3450.backtest_engine.get_profit_factor():7.4f}"
        )

        print(
            f"35.50 | "
            f"TRADES={runner_3550.backtest_engine.get_trade_count():2d} | "
            f"PROFIT={runner_3550.backtest_engine.get_total_profit():10.4f} | "
            f"PF={runner_3550.backtest_engine.get_profit_factor():7.4f}"
        )

        print()
        print("TRADE ENTRIES 34.50")
        print()

        for trade in ranges_3450:
            print(
                f"TRADE #{trade['number']:2d} | "
                f"ENTRY={trade['entry_index']:4d} | "
                f"EXIT={trade['exit_index']:4d}"
            )

        print()
        print("TRADE ENTRIES 35.50")
        print()

        for trade in ranges_3550:
            print(
                f"TRADE #{trade['number']:2d} | "
                f"ENTRY={trade['entry_index']:4d} | "
                f"EXIT={trade['exit_index']:4d}"
            )


if __name__ == "__main__":
    main()
