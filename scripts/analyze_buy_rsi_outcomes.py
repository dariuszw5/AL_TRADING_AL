from src.data.data_provider import DataProvider
from src.analysis.indicators import sma, ema, rsi
from src.strategy.basic_strategy import BasicStrategy


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALIDATION": "data/backtest/BTCUSDT_1m_validation_5000.json",
    "TEST": "data/backtest/BTCUSDT_1m_test_5000.json",
}

THRESHOLDS = [
    33.50,
    33.75,
    34.00,
    34.25,
    34.50,
    34.75,
    35.00,
    35.25,
    35.50,
    35.75,
    36.00,
    36.25,
    36.50,
]

HORIZONS = [1, 2, 3, 4, 5]


def get_buy_signals(candles):
    closes = [c.close for c in candles]

    sma_values = sma(closes, 20)
    ema_values = ema(closes, 20)
    rsi_values = rsi(closes, 14)

    strategy = BasicStrategy()

    result = {}

    for threshold in THRESHOLDS:
        result[threshold] = []

        for i in range(len(candles)):
            if i >= len(sma_values):
                continue

            if i >= len(ema_values):
                continue

            if i >= len(rsi_values):
                continue

            sma_value = sma_values[i]
            ema_value = ema_values[i]
            rsi_value = rsi_values[i]

            if sma_value is None or ema_value is None:
                continue

            if rsi_value is None:
                continue

            signal = strategy.generate_signal(
                sma_value=sma_value,
                ema_value=ema_value,
                rsi_value=rsi_value,
                min_difference=1.0,
                buy_rsi=threshold,
                sell_rsi=70.0,
            )

            if signal == "BUY":
                result[threshold].append(i)

    return result


def calculate_stats(values):
    if not values:
        return {
            "n": 0,
            "wr": 0.0,
            "avg": 0.0,
            "pf": 0.0,
            "expectancy": 0.0,
        }

    wins = [x for x in values if x > 0]
    losses = [x for x in values if x < 0]

    win_rate = len(wins) / len(values) * 100.0

    avg = sum(values) / len(values)

    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))

    if gross_loss > 0:
        profit_factor = gross_profit / gross_loss
    elif gross_profit > 0:
        profit_factor = float("inf")
    else:
        profit_factor = 0.0

    expectancy = avg

    return {
        "n": len(values),
        "wr": win_rate,
        "avg": avg,
        "pf": profit_factor,
        "expectancy": expectancy,
    }


def inspect_dataset(name, path):
    print()
    print("=" * 150)
    print(f"{name}")
    print("=" * 150)

    provider = DataProvider()
    candles = provider.load_candles(path)

    print(f"Candles: {len(candles)}")

    signals_by_threshold = get_buy_signals(candles)

    previous = set()

    for threshold in THRESHOLDS:
        current = set(signals_by_threshold[threshold])

        new_signals = sorted(current - previous)

        print()
        print(
            f"BUY RSI={threshold:.2f} | "
            f"TOTAL={len(current):3d} | "
            f"NEW={len(new_signals):3d}"
        )

        if not new_signals:
            previous = current
            continue

        for horizon in HORIZONS:
            outcomes = []

            for index in new_signals:
                future_index = index + horizon

                if future_index >= len(candles):
                    continue

                entry = candles[index].close
                exit_price = candles[future_index].close

                if entry <= 0:
                    continue

                result_pct = (
                    (exit_price - entry)
                    / entry
                    * 100.0
                )

                outcomes.append(result_pct)

            stats = calculate_stats(outcomes)

            pf_text = (
                f"{stats['pf']:.3f}"
                if stats["pf"] != float("inf")
                else "INF"
            )

            print(
                f"  +{horizon}m | "
                f"N={stats['n']:2d} | "
                f"WR={stats['wr']:6.2f}% | "
                f"AVG={stats['avg']:8.4f}% | "
                f"PF={pf_text:>7s} | "
                f"EXP={stats['expectancy']:8.4f}%"
            )

        previous = current


print("=" * 150)
print("BUY RSI INCREMENTAL OUTCOME ANALYSIS")
print("=" * 150)

for name, path in DATASETS.items():
    inspect_dataset(name, path)

print()
print("=" * 150)
print("ANALYSIS COMPLETE")
print("=" * 150)
