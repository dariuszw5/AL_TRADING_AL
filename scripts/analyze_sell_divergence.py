import json

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
HORIZON = 240


def load_candles(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def indicators(candles):
    closes = [float(c["close"]) for c in candles]

    return (
        sma(closes, 20),
        ema(closes, 20),
        rsi(closes, 14),
    )


def at(values, index, offset):
    pos = index - offset

    if pos < 0 or pos >= len(values):
        return None

    return values[pos]


def signal_at(index, sma_values, ema_values, rsi_values, sell_rsi):
    sma_value = at(sma_values, index, 19)
    ema_value = at(ema_values, index, 19)
    rsi_value = at(rsi_values, index, 14)

    if (
        sma_value is None
        or ema_value is None
        or rsi_value is None
    ):
        return "HOLD", rsi_value, None

    diff = ema_value - sma_value

    if abs(diff) < MIN_DIFFERENCE:
        return "HOLD", rsi_value, diff

    if ema_value > sma_value and rsi_value < BUY_RSI:
        return "BUY", rsi_value, diff

    if ema_value < sma_value and rsi_value > sell_rsi:
        return "SELL", rsi_value, diff

    return "HOLD", rsi_value, diff


def build_signals(candles, sell_rsi):
    sma_values, ema_values, rsi_values = indicators(candles)

    result = []

    for index in range(len(candles)):
        signal, rsi_value, diff = signal_at(
            index,
            sma_values,
            ema_values,
            rsi_values,
            sell_rsi,
        )

        result.append({
            "index": index,
            "signal": signal,
            "rsi": rsi_value,
            "diff": diff,
            "price": float(candles[index]["close"]),
        })

    return result


def run(candles, signals):
    trades = []

    position = None

    for item in signals:

        index = item["index"]

        if position is not None:

            if index - position["entry"] >= HORIZON:

                exit_price = item["price"]

                if position["side"] == "BUY":
                    profit = exit_price - position["price"]
                else:
                    profit = position["price"] - exit_price

                position["exit"] = index
                position["exit_price"] = exit_price
                position["profit"] = profit

                trades.append(position)
                position = None

        if position is not None:
            continue

        if item["signal"] in ("BUY", "SELL"):

            position = {
                "side": item["signal"],
                "entry": index,
                "price": item["price"],
                "rsi": item["rsi"],
            }

    if position is not None:

        exit_price = float(candles[-1]["close"])

        if position["side"] == "BUY":
            profit = exit_price - position["price"]
        else:
            profit = position["price"] - exit_price

        position["exit"] = len(candles) - 1
        position["exit_price"] = exit_price
        position["profit"] = profit

        trades.append(position)

    return trades


def first_divergences(trades_a, trades_b):
    entries_a = {t["entry"] for t in trades_a}
    entries_b = {t["entry"] for t in trades_b}

    all_entries = sorted(entries_a | entries_b)

    result = []

    previous_common = None

    for index in all_entries:

        in_a = index in entries_a
        in_b = index in entries_b

        if in_a != in_b:
            result.append(index)

    return result


def nearest_trade_after(trades, index):
    candidates = [
        t for t in trades
        if t["entry"] > index
    ]

    if not candidates:
        return None

    return min(
        candidates,
        key=lambda t: t["entry"]
    )


def print_trade(label, trade):
    if trade is None:
        print(f"{label}: NONE")
        return

    print(
        f"{label}: "
        f"{trade['side']} "
        f"{trade['entry']} -> {trade['exit']} "
        f"P/L={trade['profit']:+.2f}"
    )


def main():

    for dataset_name, path in DATASETS.items():

        candles = load_candles(path)

        signals_a = build_signals(
            candles,
            SELL_A,
        )

        signals_b = build_signals(
            candles,
            SELL_B,
        )

        trades_a = run(candles, signals_a)
        trades_b = run(candles, signals_b)

        entries_a = {t["entry"] for t in trades_a}
        entries_b = {t["entry"] for t in trades_b}

        divergence_points = sorted(
            entries_a ^ entries_b
        )

        print()
        print("=" * 120)
        print(
            f"{dataset_name} | FIRST TRADE DIVERGENCES | "
            f"SELL {SELL_A:.2f} vs SELL {SELL_B:.2f}"
        )
        print("=" * 120)

        print()
        print(
            f"SELL {SELL_A:.2f}: "
            f"{len(trades_a)} trades | "
            f"P/L={sum(t['profit'] for t in trades_a):+.2f}"
        )

        print(
            f"SELL {SELL_B:.2f}: "
            f"{len(trades_b)} trades | "
            f"P/L={sum(t['profit'] for t in trades_b):+.2f}"
        )

        print()

        for divergence in divergence_points:

            sig_a = signals_a[divergence]
            sig_b = signals_b[divergence]

            trade_a = next(
                (
                    t for t in trades_a
                    if t["entry"] == divergence
                ),
                None,
            )

            trade_b = next(
                (
                    t for t in trades_b
                    if t["entry"] == divergence
                ),
                None,
            )

            print("-" * 120)

            print(
                f"INDEX {divergence} | "
                f"PRICE={sig_a['price']:.2f} | "
                f"RSI={sig_a['rsi']:.4f} | "
                f"EMA-SMA={sig_a['diff']:+.4f}"
            )

            print(
                f"SIGNAL: "
                f"SELL{SELL_A:.0f}={sig_a['signal']} | "
                f"SELL{SELL_B:.0f}={sig_b['signal']}"
            )

            print_trade(
                f"TRADE {SELL_A:.0f}",
                trade_a,
            )

            print_trade(
                f"TRADE {SELL_B:.0f}",
                trade_b,
            )

            next_a = nearest_trade_after(
                trades_a,
                divergence,
            )

            next_b = nearest_trade_after(
                trades_b,
                divergence,
            )

            if trade_a is None:
                print_trade(
                    f"NEXT {SELL_A:.0f}",
                    next_a,
                )

            if trade_b is None:
                print_trade(
                    f"NEXT {SELL_B:.0f}",
                    next_b,
                )

        print()
        print(
            f"TRADE ENTRY DIVERGENCES: "
            f"{len(divergence_points)}"
        )


if __name__ == "__main__":
    main()
