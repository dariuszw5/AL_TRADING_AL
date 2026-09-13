import json

from src.backtest.backtest_runner import BacktestRunner
from src.analysis.indicators import sma, ema, rsi


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALIDATION": "data/backtest/BTCUSDT_1m_validation_5000.json",
    "TEST": "data/backtest/BTCUSDT_1m_test_5000.json",
}

BUY_RSI = 35.50
SELL_A = 69.0
SELL_B = 77.0
MIN_DIFFERENCE = 1.0


def load_candles(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_price(candle):
    return float(candle["close"])


def get_indicator_values(candles):
    closes = [float(c["close"]) for c in candles]

    sma_values = sma(closes, 20)
    ema_values = ema(closes, 20)
    rsi_values = rsi(closes, 14)

    return sma_values, ema_values, rsi_values


def value_at(values, index, offset):
    pos = index - offset

    if pos < 0 or pos >= len(values):
        return None

    return values[pos]


def signal_at(candles, index, sma_values, ema_values, rsi_values, sell_rsi):
    sma_value = value_at(sma_values, index, 19)
    ema_value = value_at(ema_values, index, 19)
    rsi_value = value_at(rsi_values, index, 14)

    if sma_value is None or ema_value is None or rsi_value is None:
        return "HOLD", None, None, None

    difference = abs(ema_value - sma_value)

    if difference < MIN_DIFFERENCE:
        return "HOLD", rsi_value, ema_value - sma_value, difference

    if ema_value > sma_value and rsi_value < BUY_RSI:
        return "BUY", rsi_value, ema_value - sma_value, difference

    if ema_value < sma_value and rsi_value > sell_rsi:
        return "SELL", rsi_value, ema_value - sma_value, difference

    return "HOLD", rsi_value, ema_value - sma_value, difference


def run(path, sell_rsi):
    runner = BacktestRunner(
        symbol="BTCUSDT",
        interval="1m",
        limit=5000,
        initial_balance=1000.0,
        buy_rsi=BUY_RSI,
        sell_rsi=sell_rsi,
        min_difference=MIN_DIFFERENCE,
        trading_fee=0.0,
        rsi_method="classic",
        data_source="file",
        data_file=path,
    )

    runner.load_data()
    runner.run()

    return runner


def get_trades(runner):
    return runner.backtest_engine.get_trades()


def trade_value(trade, *names):
    for name in names:
        if isinstance(trade, dict) and name in trade:
            return trade[name]

        if hasattr(trade, name):
            return getattr(trade, name)

    return None


def timestamp_to_index(candles):
    result = {}

    for i, candle in enumerate(candles):
        result[int(candle["timestamp"])] = i

    return result


def trade_indices(trade, ts_index):
    entry_ts = trade_value(trade, "entry_timestamp", "entry_time")
    exit_ts = trade_value(trade, "exit_timestamp", "exit_time")

    if entry_ts is not None:
        entry_ts = int(entry_ts)

    if exit_ts is not None:
        exit_ts = int(exit_ts)

    return ts_index.get(entry_ts), ts_index.get(exit_ts)


def main():

    for dataset_name, path in DATASETS.items():

        candles = load_candles(path)
        ts_index = timestamp_to_index(candles)

        sma_values, ema_values, rsi_values = get_indicator_values(candles)

        runner_a = run(path, SELL_A)
        runner_b = run(path, SELL_B)

        trades_a = get_trades(runner_a)
        trades_b = get_trades(runner_b)

        ranges_a = []
        ranges_b = []

        for trade in trades_a:
            entry, exit_ = trade_indices(trade, ts_index)
            ranges_a.append((entry, exit_, trade))

        for trade in trades_b:
            entry, exit_ = trade_indices(trade, ts_index)
            ranges_b.append((entry, exit_, trade))

        print()
        print("=" * 130)
        print(f"{dataset_name} | FIRST DIVERGENCES | SELL {SELL_A:.2f} vs SELL {SELL_B:.2f}")
        print("=" * 130)

        print()
        print(
            f"SELL {SELL_A:.2f}: "
            f"{len(trades_a)} trades | "
            f"profit={runner_a.backtest_engine.get_total_profit():+.4f}"
        )

        print(
            f"SELL {SELL_B:.2f}: "
            f"{len(trades_b)} trades | "
            f"profit={runner_b.backtest_engine.get_total_profit():+.4f}"
        )

        print()
        print("--- TRADE SEQUENCES ---")

        max_len = max(len(ranges_a), len(ranges_b))

        for i in range(max_len):

            a = ranges_a[i] if i < len(ranges_a) else None
            b = ranges_b[i] if i < len(ranges_b) else None

            if a:
                a_entry, a_exit, a_trade = a
                a_side = trade_value(a_trade, "side")
                a_profit = trade_value(a_trade, "profit", "pnl", "profit_loss")
            else:
                a_entry = a_exit = a_side = a_profit = None

            if b:
                b_entry, b_exit, b_trade = b
                b_side = trade_value(b_trade, "side")
                b_profit = trade_value(b_trade, "profit", "pnl", "profit_loss")
            else:
                b_entry = b_exit = b_side = b_profit = None

            same = (
                a_entry == b_entry
                and a_exit == b_exit
                and a_side == b_side
            )

            marker = "SAME" if same else "<<< DIVERGENCE"

            print(
                f"#{i+1:02d} | "
                f"69: {a_side} {a_entry}->{a_exit} "
                f"profit={a_profit} | "
                f"77: {b_side} {b_entry}->{b_exit} "
                f"profit={b_profit} | "
                f"{marker}"
            )

        print()
        print("--- FIRST 10 SIGNAL DIVERGENCES ---")

        found = 0

        for index in range(len(candles)):

            signal_a, rsi_a, diff_a, absdiff_a = signal_at(
                candles,
                index,
                sma_values,
                ema_values,
                rsi_values,
                SELL_A,
            )

            signal_b, rsi_b, diff_b, absdiff_b = signal_at(
                candles,
                index,
                sma_values,
                ema_values,
                rsi_values,
                SELL_B,
            )

            if signal_a == signal_b:
                continue

            print(
                f"INDEX={index:4d} | "
                f"RSI={rsi_a:8.4f} | "
                f"EMA-SMA={diff_a:9.4f} | "
                f"SELL69={signal_a:<4} | "
                f"SELL77={signal_b:<4} | "
                f"CLOSE={get_price(candles[index]):.2f}"
            )

            found += 1

            if found >= 10:
                break


if __name__ == "__main__":
    main()
