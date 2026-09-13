from src.data.data_provider import DataProvider
from src.analysis.market_analyzer import MarketAnalyzer


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALIDATION": "data/backtest/BTCUSDT_1m_validation_5000.json",
}

BUY_RSI = 30.0
SELL_RSI = 70.0
MIN_DIFFERENCE = 1.0
HORIZONS = [30, 60, 120, 240]


def load_candles(path):
    provider = DataProvider()
    return provider.load_candles(path)


def calculate_volatility(candles, index, window):
    if index < window:
        return None

    returns = []

    for i in range(index - window + 1, index + 1):
        previous_close = candles[i - 1].close
        current_close = candles[i].close

        if previous_close == 0:
            continue

        returns.append(
            abs((current_close - previous_close) / previous_close) * 100.0
        )

    return sum(returns) / len(returns) if returns else None


def calculate_range(candles, index, window):
    if index < window:
        return None

    start_price = candles[index - window].close
    end_price = candles[index].close

    if start_price == 0:
        return None

    return abs((end_price - start_price) / start_price) * 100.0


def calculate_atr(candles, index, period=14):
    if index < period:
        return None

    true_ranges = []

    for i in range(index - period + 1, index + 1):
        high = candles[i].high
        low = candles[i].low
        previous_close = candles[i - 1].close

        tr = max(
            high - low,
            abs(high - previous_close),
            abs(low - previous_close),
        )

        if previous_close != 0:
            true_ranges.append((tr / previous_close) * 100.0)

    return sum(true_ranges) / len(true_ranges) if true_ranges else None


def build_signal(candles, index, analyzer):
    if index < 20:
        return "HOLD"

    analysis = analyzer.analyze(candles[:index + 1])

    sma_values = analysis.get("sma", [])
    ema_values = analysis.get("ema", [])
    rsi_values = analysis.get("rsi", [])

    if not sma_values or not ema_values or not rsi_values:
        return "HOLD"

    sma = sma_values[-1]
    ema = ema_values[-1]
    rsi = rsi_values[-1]

    if abs(ema - sma) < MIN_DIFFERENCE:
        return "HOLD"

    if ema > sma and rsi < BUY_RSI:
        return "BUY"

    if ema < sma and rsi > SELL_RSI:
        return "SELL"

    return "HOLD"


def forward_return(candles, index, horizon, side):
    target = index + horizon

    if target >= len(candles):
        return None

    entry = candles[index].close
    future = candles[target].close

    if entry == 0:
        return None

    if side == "BUY":
        return ((future - entry) / entry) * 100.0

    return ((entry - future) / entry) * 100.0


def bucket_stats(rows, horizon):
    values = [
        row["returns"][horizon]
        for row in rows
        if row["returns"].get(horizon) is not None
    ]

    if not values:
        return None

    wins = [x for x in values if x > 0]
    losses = [x for x in values if x < 0]

    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))

    if gross_loss == 0:
        pf = float("inf") if gross_profit > 0 else 0.0
    else:
        pf = gross_profit / gross_loss

    return {
        "n": len(values),
        "wr": len(wins) / len(values) * 100.0,
        "avg": sum(values) / len(values),
        "sum": sum(values),
        "pf": pf,
    }


def print_stats(title, rows):
    print(f"\n{title}")

    if not rows:
        print("  BRAK DANYCH")
        return

    for horizon in HORIZONS:
        stats = bucket_stats(rows, horizon)

        if stats is None:
            continue

        pf = "INF" if stats["pf"] == float("inf") else f"{stats['pf']:.3f}"

        print(
            f"  {horizon:>3}m | "
            f"N={stats['n']:>2} | "
            f"WR={stats['wr']:>6.2f}% | "
            f"AVG={stats['avg']:>+8.4f}% | "
            f"SUM={stats['sum']:>+9.4f}% | "
            f"PF={pf:>6}"
        )


def analyze_dataset(name, path):
    print("\n" + "=" * 90)
    print(name)
    print("=" * 90)

    candles = load_candles(path)
    analyzer = MarketAnalyzer(rsi_method="classic")

    rows = []

    for index in range(30, len(candles)):
        signal = build_signal(candles, index, analyzer)

        if signal not in ("BUY", "SELL"):
            continue

        vol_5 = calculate_volatility(candles, index, 5)
        vol_15 = calculate_volatility(candles, index, 15)
        vol_30 = calculate_volatility(candles, index, 30)

        range_5 = calculate_range(candles, index, 5)
        range_15 = calculate_range(candles, index, 15)
        range_30 = calculate_range(candles, index, 30)

        atr = calculate_atr(candles, index, 14)

        values = [
            vol_5,
            vol_15,
            vol_30,
            range_5,
            range_15,
            range_30,
            atr,
        ]

        if any(v is None for v in values):
            continue

        returns = {
            horizon: forward_return(candles, index, horizon, signal)
            for horizon in HORIZONS
        }

        rows.append({
            "signal": signal,
            "vol_5": vol_5,
            "vol_15": vol_15,
            "vol_30": vol_30,
            "range_5": range_5,
            "range_15": range_15,
            "range_30": range_30,
            "atr": atr,
            "returns": returns,
        })

    print(f"Sygnały: {len(rows)}")

    for side in ("BUY", "SELL"):
        side_rows = [r for r in rows if r["signal"] == side]

        print("\n" + "-" * 90)
        print(f"{side} | N={len(side_rows)}")
        print("-" * 90)

        metrics = (
            "vol_5",
            "vol_15",
            "vol_30",
            "range_5",
            "range_15",
            "range_30",
            "atr",
        )

        for metric in metrics:
            values = sorted(r[metric] for r in side_rows)

            if len(values) < 3:
                continue

            low_threshold = values[len(values) // 3]
            high_threshold = values[(len(values) * 2) // 3]

            low = [
                r for r in side_rows
                if r[metric] < low_threshold
            ]

            normal = [
                r for r in side_rows
                if low_threshold <= r[metric] <= high_threshold
            ]

            high = [
                r for r in side_rows
                if r[metric] > high_threshold
            ]

            print(f"\n### {metric.upper()}")
            print(
                f"Progi: LOW < {low_threshold:.5f}% | "
                f"HIGH > {high_threshold:.5f}%"
            )

            print_stats("LOW", low)
            print_stats("NORMAL", normal)
            print_stats("HIGH", high)


def main():
    print("=" * 90)
    print("VOLATILITY / MARKET REGIME DIAGNOSTIC")
    print("=" * 90)

    for name, path in DATASETS.items():
        analyze_dataset(name, path)

    print("\n" + "=" * 90)
    print("KONIEC")
    print("=" * 90)


if __name__ == "__main__":
    main()
