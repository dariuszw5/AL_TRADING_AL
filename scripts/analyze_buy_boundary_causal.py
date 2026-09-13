from src.backtest.backtest_runner import BacktestRunner
from src.analysis.indicators import sma, ema, rsi


DATASETS = {
    "VALIDATION": "data/backtest/BTCUSDT_1m_validation_5000.json",
    "TEST": "data/backtest/BTCUSDT_1m_test_5000.json",
}

SELL_RSI = 68.50
FEE = 0.0004
MIN_DIFF = 1.0
RSI_METHOD = "classic"


def run(dataset, buy_rsi):
    runner = BacktestRunner(
        symbol="BTCUSDT",
        interval="1m",
        limit=5000,
        initial_balance=1000.0,
        buy_rsi=buy_rsi,
        sell_rsi=SELL_RSI,
        min_difference=MIN_DIFF,
        trading_fee=FEE,
        rsi_method=RSI_METHOD,
        data_source="file",
        data_file=DATASETS[dataset],
    )

    runner.load_data()
    runner.run()

    return runner


def calculate_indicators(candles):
    closes = [c.close for c in candles]

    sma_values = sma(closes, 20)
    ema_values = ema(closes, 20)

    if RSI_METHOD == "classic":
        rsi_values = rsi(closes, 14)
    else:
        rsi_values = rsi(closes, 14, method=RSI_METHOD)

    return sma_values, ema_values, rsi_values


def get_indicator_at_index(
    sma_values,
    ema_values,
    rsi_values,
    index,
):
    sma_index = index - 19
    ema_index = index - 19
    rsi_index = index - 14

    if sma_index < 0 or ema_index < 0 or rsi_index < 0:
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
        rsi_values[rsi_index],
    )


def print_region(dataset, center_index, low_threshold, high_threshold):
    runner = run(dataset, low_threshold)

    sma_values, ema_values, rsi_values = calculate_indicators(
        runner.candles
    )

    print()
    print("=" * 120)
    print(
        f"{dataset} | CENTER={center_index} | "
        f"BUY {low_threshold:.5f} -> {high_threshold:.5f}"
    )
    print("=" * 120)

    start = max(0, center_index - 12)
    end = min(len(runner.candles), center_index + 13)

    for index in range(start, end):
        values = get_indicator_at_index(
            sma_values,
            ema_values,
            rsi_values,
            index,
        )

        if values is None:
            continue

        sma_value, ema_value, rsi_value = values
        difference = abs(ema_value - sma_value)

        buy_low = (
            difference >= MIN_DIFF
            and ema_value > sma_value
            and rsi_value < low_threshold
        )

        buy_high = (
            difference >= MIN_DIFF
            and ema_value > sma_value
            and rsi_value < high_threshold
        )

        sell = (
            difference >= MIN_DIFF
            and ema_value < sma_value
            and rsi_value > SELL_RSI
        )

        marker = ""

        if low_threshold <= rsi_value <= high_threshold:
            marker = " <<< BOUNDARY RSI"

        if buy_low != buy_high:
            marker += " <<< SIGNAL DIFFERENCE"

        candle = runner.candles[index]

        print(
            f"IDX={index:4d} "
            f"TS={candle.timestamp} "
            f"CLOSE={candle.close:10.2f} "
            f"RSI={rsi_value:11.8f} "
            f"SMA={sma_value:11.2f} "
            f"EMA={ema_value:11.2f} "
            f"ABS_DIFF={difference:9.4f} "
            f"BUY_LOW={str(buy_low):5s} "
            f"BUY_HIGH={str(buy_high):5s} "
            f"SELL={str(sell):5s}"
            f"{marker}"
        )


def find_boundary_values(dataset, low_threshold, high_threshold):
    runner = run(dataset, low_threshold)

    sma_values, ema_values, rsi_values = calculate_indicators(
        runner.candles
    )

    print()
    print("=" * 120)
    print(
        f"{dataset} | ALL RSI VALUES BETWEEN "
        f"{low_threshold:.5f} AND {high_threshold:.5f}"
    )
    print("=" * 120)

    found = []

    for index in range(len(runner.candles)):
        values = get_indicator_at_index(
            sma_values,
            ema_values,
            rsi_values,
            index,
        )

        if values is None:
            continue

        sma_value, ema_value, rsi_value = values

        if low_threshold <= rsi_value <= high_threshold:
            difference = abs(ema_value - sma_value)

            candle = runner.candles[index]

            buy_low = (
                difference >= MIN_DIFF
                and ema_value > sma_value
                and rsi_value < low_threshold
            )

            buy_high = (
                difference >= MIN_DIFF
                and ema_value > sma_value
                and rsi_value < high_threshold
            )

            found.append(
                (
                    index,
                    candle.timestamp,
                    candle.close,
                    rsi_value,
                    sma_value,
                    ema_value,
                    difference,
                    buy_low,
                    buy_high,
                )
            )

    if not found:
        print("BRAK RSI W PODANYM PRZEDZIALE.")
        return

    for row in found:
        (
            index,
            timestamp,
            close,
            rsi_value,
            sma_value,
            ema_value,
            difference,
            buy_low,
            buy_high,
        ) = row

        print(
            f"IDX={index:4d} "
            f"TS={timestamp} "
            f"CLOSE={close:10.2f} "
            f"RSI={rsi_value:12.9f} "
            f"SMA={sma_value:11.2f} "
            f"EMA={ema_value:11.2f} "
            f"ABS_DIFF={difference:9.4f} "
            f"BUY_LOW={buy_low} "
            f"BUY_HIGH={buy_high}"
        )


print()
print("=" * 120)
print("VALIDATION CAUSAL BOUNDARY")
print("=" * 120)

find_boundary_values(
    "VALIDATION",
    34.10,
    34.20,
)

print_region(
    "VALIDATION",
    3694,
    34.10,
    34.20,
)


print()
print("=" * 120)
print("TEST CAUSAL BOUNDARY")
print("=" * 120)

find_boundary_values(
    "TEST",
    34.45,
    34.49,
)

print_region(
    "TEST",
    805,
    34.45,
    34.49,
)


print()
print("=" * 120)
print("END")
print("=" * 120)
