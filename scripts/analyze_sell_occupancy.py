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


def get_indicators(candles):
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
        return "HOLD", None, None

    difference = abs(ema_value - sma_value)
    ema_minus_sma = ema_value - sma_value

    if difference < MIN_DIFFERENCE:
        return "HOLD", rsi_value, ema_minus_sma

    if ema_value > sma_value and rsi_value < BUY_RSI:
        return "BUY", rsi_value, ema_minus_sma

    if ema_value < sma_value and rsi_value > sell_rsi:
        return "SELL", rsi_value, ema_minus_sma

    return "HOLD", rsi_value, ema_minus_sma


def generate_signals(candles, sell_rsi):
    sma_values, ema_values, rsi_values = get_indicators(candles)

    signals = []

    for index in range(len(candles)):
        signal, rsi_value, diff = signal_at(
            index,
            sma_values,
            ema_values,
            rsi_values,
            sell_rsi,
        )

        signals.append({
            "index": index,
            "signal": signal,
            "rsi": rsi_value,
            "diff": diff,
            "price": float(candles[index]["close"]),
        })

    return signals


def run_shadow(candles, signals):
    """
    Uproszczony model occupancy:
    - wejście natychmiast na sygnale,
    - maksymalny czas pozycji = 240 świec,
    - brak SL/TP,
    - kolejny sygnał jest ignorowany, gdy pozycja jest otwarta.
    """

    trades = []
    blocked = []

    position = None

    for item in signals:
        index = item["index"]

        # TIME EXIT
        if position is not None:
            if index - position["entry_index"] >= HORIZON:

                exit_price = item["price"]

                if position["side"] == "BUY":
                    profit = exit_price - position["entry_price"]
                else:
                    profit = position["entry_price"] - exit_price

                position["exit_index"] = index
                position["exit_price"] = exit_price
                position["profit"] = profit

                trades.append(position)

                position = None

        if position is not None:

            if item["signal"] in ("BUY", "SELL"):
                blocked.append({
                    "index": index,
                    "signal": item["signal"],
                    "price": item["price"],
                    "rsi": item["rsi"],
                    "diff": item["diff"],
                    "blocked_by": position["side"],
                    "blocked_since": position["entry_index"],
                })

            continue

        if item["signal"] == "BUY":
            position = {
                "side": "BUY",
                "entry_index": index,
                "entry_price": item["price"],
                "entry_rsi": item["rsi"],
            }

        elif item["signal"] == "SELL":
            position = {
                "side": "SELL",
                "entry_index": index,
                "entry_price": item["price"],
                "entry_rsi": item["rsi"],
            }

    # END OF DATA
    if position is not None:

        exit_price = float(candles[-1]["close"])

        if position["side"] == "BUY":
            profit = exit_price - position["entry_price"]
        else:
            profit = position["entry_price"] - exit_price

        position["exit_index"] = len(candles) - 1
        position["exit_price"] = exit_price
        position["profit"] = profit

        trades.append(position)

    return trades, blocked


def trade_map(trades):
    return {
        trade["entry_index"]: trade
        for trade in trades
    }


def main():

    for dataset_name, path in DATASETS.items():

        candles = load_candles(path)

        signals_a = generate_signals(candles, SELL_A)
        signals_b = generate_signals(candles, SELL_B)

        trades_a, blocked_a = run_shadow(
            candles,
            signals_a,
        )

        trades_b, blocked_b = run_shadow(
            candles,
            signals_b,
        )

        print()
        print("=" * 125)
        print(
            f"{dataset_name} | OCCUPANCY / OPPORTUNITY COST | "
            f"SELL {SELL_A:.2f} vs SELL {SELL_B:.2f}"
        )
        print("=" * 125)

        profit_a = sum(
            t["profit"] for t in trades_a
        )

        profit_b = sum(
            t["profit"] for t in trades_b
        )

        print()
        print(
            f"SELL {SELL_A:.2f}: "
            f"TRADES={len(trades_a):3d} | "
            f"SHADOW P/L={profit_a:+10.2f}"
        )

        print(
            f"SELL {SELL_B:.2f}: "
            f"TRADES={len(trades_b):3d} | "
            f"SHADOW P/L={profit_b:+10.2f}"
        )

        print(
            f"DIFFERENCE: "
            f"{profit_b - profit_a:+.2f}"
        )

        print()
        print(
            f"BLOCKED SIGNALS BY SELL {SELL_A:.2f}: "
            f"{len(blocked_a)}"
        )

        print(
            f"BLOCKED SIGNALS BY SELL {SELL_B:.2f}: "
            f"{len(blocked_b)}"
        )

        print()
        print(
            "=== SIGNALS TAKEN BY 77 BUT BLOCKED BY 69 ==="
        )

        print(
            "INDEX | SIGNAL | RSI      | PRICE      | "
            "69 BLOCKING POSITION"
        )
        print("-" * 90)

        map_a = trade_map(trades_a)

        count = 0

        for item in blocked_a:

            signal_b = signals_b[item["index"]]["signal"]

            if signal_b not in ("BUY", "SELL"):
                continue

            # 69 blocked this signal.
            # Check whether 77 was actually able to take it.
            blocked_by_a = item["blocked_by"]

            print(
                f"{item['index']:5d} | "
                f"{signal_b:6s} | "
                f"{item['rsi']:8.4f} | "
                f"{item['price']:10.2f} | "
                f"{blocked_by_a:4s} @ "
                f"{item['blocked_since']}"
            )

            count += 1

        print()
        print(
            f"OPPORTUNITIES BLOCKED BY SELL {SELL_A:.2f}: "
            f"{count}"
        )

        print()
        print(
            "=== TRADES UNIQUE TO EACH VERSION ==="
        )

        entries_a = {
            t["entry_index"]
            for t in trades_a
        }

        entries_b = {
            t["entry_index"]
            for t in trades_b
        }

        only_a = sorted(entries_a - entries_b)
        only_b = sorted(entries_b - entries_a)

        print()
        print(
            f"ONLY SELL {SELL_A:.2f}: "
            f"{len(only_a)} trades"
        )

        for index in only_a:
            trade = map_a[index]

            print(
                f"  {trade['side']:4s} "
                f"{trade['entry_index']:5d}"
                f" -> {trade['exit_index']:5d} "
                f"P/L={trade['profit']:+.2f}"
            )

        map_b = trade_map(trades_b)

        print()
        print(
            f"ONLY SELL {SELL_B:.2f}: "
            f"{len(only_b)} trades"
        )

        for index in only_b:
            trade = map_b[index]

            print(
                f"  {trade['side']:4s} "
                f"{trade['entry_index']:5d}"
                f" -> {trade['exit_index']:5d} "
                f"P/L={trade['profit']:+.2f}"
            )


if __name__ == "__main__":
    main()
