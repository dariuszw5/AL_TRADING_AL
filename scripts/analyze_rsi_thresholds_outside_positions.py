from src.data.data_provider import DataProvider
from src.backtest.backtest_runner import BacktestRunner
from src.analysis.indicators import sma, ema, rsi
from src.strategy.basic_strategy import BasicStrategy


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALIDATION": "data/backtest/BTCUSDT_1m_validation_5000.json",
    "TEST": "data/backtest/BTCUSDT_1m_test_5000.json",
}

THRESHOLDS = [
    34.75,
    35.00,
    35.25,
    35.50,
    35.75,
    36.00,
]


def get_signals(data, buy_rsi):
    strategy = BasicStrategy()
    signals = {}

    for i in range(20, len(data)):
        closes = [c.close for c in data[:i + 1]]

        sma_values = sma(closes, 20)
        ema_values = ema(closes, 20)
        rsi_values = rsi(closes, 14)

        if not sma_values or not ema_values or not rsi_values:
            continue

        sma_value = sma_values[-1]
        ema_value = ema_values[-1]
        rsi_value = rsi_values[-1]

        signal = strategy.generate_signal(
            sma_value=sma_value,
            ema_value=ema_value,
            rsi_value=rsi_value,
            buy_rsi=buy_rsi,
            sell_rsi=70.0,
            min_difference=1.0,
        )

        if signal == "BUY":
            signals[data[i].timestamp] = {
                "index": i,
                "timestamp": data[i].timestamp,
                "rsi": rsi_value,
                "ema_sma": abs(ema_value - sma_value),
                "entry": data[i].close,
            }

    return signals


def get_trade_ranges(runner, data):
    trades = runner.backtest_engine.get_trades()
    ranges = []

    for number, trade in enumerate(trades, start=1):
        if not isinstance(trade, dict):
            continue

        entry_timestamp = trade.get("entry_timestamp")
        exit_timestamp = trade.get("exit_timestamp")

        entry_index = None
        exit_index = None

        if entry_timestamp is not None:
            for i, candle in enumerate(data):
                if candle.timestamp == entry_timestamp:
                    entry_index = i
                    break

        if exit_timestamp is not None:
            for i, candle in enumerate(data):
                if candle.timestamp == exit_timestamp:
                    exit_index = i
                    break

        if entry_index is not None:
            ranges.append(
                {
                    "number": number,
                    "entry_index": entry_index,
                    "exit_index": exit_index,
                }
            )

    return ranges


def is_inside_trade(index, trade_ranges):
    for trade in trade_ranges:
        entry_index = trade["entry_index"]
        exit_index = trade["exit_index"]

        if exit_index is None:
            if index >= entry_index:
                return True, trade

        elif entry_index <= index <= exit_index:
            return True, trade

    return False, None


def main():
    provider = DataProvider()

    for name, path in DATASETS.items():
        print()
        print("=" * 110)
        print(f"{name} | NEW BUY SIGNALS OUTSIDE EXISTING POSITIONS")
        print("=" * 110)

        data = provider.load_candles(path)

        runner = BacktestRunner(
            symbol="BTCUSDT",
            interval="1m",
            limit=5000,
            initial_balance=1000.0,
            buy_rsi=34.75,
            sell_rsi=70.0,
            min_difference=1.0,
            trading_fee=0.0,
            rsi_method="classic",
            data_source="file",
            data_file=path,
        )

        runner.load_data()
        runner.run()

        trade_ranges = get_trade_ranges(runner, data)

        previous_signals = get_signals(data, 34.50)

        print(
            f"BASE RSI 34.50 SIGNALS: {len(previous_signals)}"
        )
        print(
            f"BACKTEST TRADES: {len(trade_ranges)}"
        )
        print()

        previous_timestamps = set(previous_signals)

        for threshold in THRESHOLDS:
            current_signals = get_signals(data, threshold)

            new_timestamps = sorted(
                set(current_signals) - previous_timestamps
            )

            outside = []

            for timestamp in new_timestamps:
                signal = current_signals[timestamp]

                inside, trade = is_inside_trade(
                    signal["index"],
                    trade_ranges
                )

                if not inside:
                    outside.append(signal)

            print(
                f"RSI {threshold:5.2f} | "
                f"NEW SIGNALS={len(new_timestamps):2d} | "
                f"OUTSIDE POSITIONS={len(outside):2d}"
            )

            for signal in outside:
                i = signal["index"]

                ret1 = None
                ret5 = None
                ret15 = None
                ret30 = None

                if i + 1 < len(data):
                    ret1 = (
                        (data[i + 1].close - signal["entry"])
                        / signal["entry"]
                        * 100
                    )

                if i + 5 < len(data):
                    ret5 = (
                        (data[i + 5].close - signal["entry"])
                        / signal["entry"]
                        * 100
                    )

                if i + 15 < len(data):
                    ret15 = (
                        (data[i + 15].close - signal["entry"])
                        / signal["entry"]
                        * 100
                    )

                if i + 30 < len(data):
                    ret30 = (
                        (data[i + 30].close - signal["entry"])
                        / signal["entry"]
                        * 100
                    )

                print(
                    f"    INDEX={i:4d} | "
                    f"RSI={signal['rsi']:6.2f} | "
                    f"EMA-SMA={signal['ema_sma']:7.2f} | "
                    f"ENTRY={signal['entry']:10.2f} | "
                    f"+1m={ret1:+.4f}% | "
                    f"+5m={ret5:+.4f}% | "
                    f"+15m={ret15:+.4f}% | "
                    f"+30m={ret30:+.4f}%"
                )

            previous_timestamps = set(current_signals)

        print()
        print("-" * 110)


if __name__ == "__main__":
    main()
