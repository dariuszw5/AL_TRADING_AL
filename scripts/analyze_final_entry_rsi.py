from src.data.data_provider import DataProvider
from src.analysis.indicators import sma, ema, rsi
from src.strategy.basic_strategy import BasicStrategy


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALIDATION": "data/backtest/BTCUSDT_1m_validation_5000.json",
    "TEST": "data/backtest/BTCUSDT_1m_test_5000.json",
}

BUY_RSI = 34.50
SELL_RSI = 68.50
MIN_DIFF = 1.0

SMA_PERIOD = 20
EMA_PERIOD = 20
RSI_PERIOD = 14


def load_candles(path):
    provider = DataProvider()
    return provider.load_candles(path)


def main():
    strategy = BasicStrategy()

    for name, path in DATASETS.items():
        print("\n" + "=" * 110)
        print(f"=== {name} ENTRY RSI ANALYSIS ===")
        print("=" * 110)

        candles = load_candles(path)
        closes = [float(c.close) for c in candles]

        sma_values = sma(closes, SMA_PERIOD)
        ema_values = ema(closes, EMA_PERIOD)
        rsi_values = rsi(closes, RSI_PERIOD)

        signals = []

        # Wskaźniki są skrócone:
        # SMA/EMA zaczynają się od indeksu period-1
        # RSI zaczyna się od indeksu period
        start_index = max(
            SMA_PERIOD - 1,
            EMA_PERIOD - 1,
            RSI_PERIOD
        )

        for i in range(start_index, len(candles)):
            sma_index = i - (SMA_PERIOD - 1)
            ema_index = i - (EMA_PERIOD - 1)
            rsi_index = i - RSI_PERIOD

            if (
                sma_index < 0
                or ema_index < 0
                or rsi_index < 0
                or sma_index >= len(sma_values)
                or ema_index >= len(ema_values)
                or rsi_index >= len(rsi_values)
            ):
                continue

            sma_value = float(sma_values[sma_index])
            ema_value = float(ema_values[ema_index])
            rsi_value = float(rsi_values[rsi_index])

            signal = strategy.generate_signal(
                sma_value=sma_value,
                ema_value=ema_value,
                rsi_value=rsi_value,
                min_difference=MIN_DIFF,
                buy_rsi=BUY_RSI,
                sell_rsi=SELL_RSI,
            )

            if signal in ("BUY", "SELL"):
                if signal == "BUY":
                    distance = rsi_value - BUY_RSI
                else:
                    distance = rsi_value - SELL_RSI

                signals.append({
                    "index": i,
                    "side": signal,
                    "rsi": rsi_value,
                    "distance": distance,
                    "sma": sma_value,
                    "ema": ema_value,
                    "difference": abs(ema_value - sma_value),
                    "price": float(candles[i].close),
                    "timestamp": candles[i].timestamp,
                })

        print(
            f"\nCONFIG: BUY={BUY_RSI:.2f} | "
            f"SELL={SELL_RSI:.2f} | "
            f"MIN_DIFF={MIN_DIFF:.2f} | "
            f"RSI=classic"
        )

        print(
            f"SMA={SMA_PERIOD} | "
            f"EMA={EMA_PERIOD} | "
            f"RSI_PERIOD={RSI_PERIOD}"
        )

        print("\nALL SIGNALS")
        print("-" * 110)
        print(
            "SIGNAL | INDEX |      RSI | DISTANCE | "
            "EMA-SMA |       PRICE | TIMESTAMP"
        )
        print("-" * 110)

        for signal in signals:
            print(
                f"{signal['side']:6s} | "
                f"{signal['index']:5d} | "
                f"{signal['rsi']:8.2f} | "
                f"{signal['distance']:8.2f} | "
                f"{signal['ema'] - signal['sma']:8.2f} | "
                f"{signal['price']:11.2f} | "
                f"{signal['timestamp']}"
            )

        buy = [s for s in signals if s["side"] == "BUY"]
        sell = [s for s in signals if s["side"] == "SELL"]

        print("\nSUMMARY")
        print("-" * 110)

        print(f"TOTAL SIGNALS: {len(signals)}")
        print(f"BUY SIGNALS  : {len(buy)}")
        print(f"SELL SIGNALS : {len(sell)}")

        if buy:
            values = [s["rsi"] for s in buy]
            distances = [s["distance"] for s in buy]

            print(
                f"\nBUY RSI : "
                f"MIN={min(values):.2f} | "
                f"MAX={max(values):.2f} | "
                f"AVG={sum(values)/len(values):.2f}"
            )

            print(
                f"BUY DIST: "
                f"MIN={min(distances):.2f} | "
                f"MAX={max(distances):.2f} | "
                f"AVG={sum(distances)/len(distances):.2f}"
            )

        if sell:
            values = [s["rsi"] for s in sell]
            distances = [s["distance"] for s in sell]

            print(
                f"\nSELL RSI: "
                f"MIN={min(values):.2f} | "
                f"MAX={max(values):.2f} | "
                f"AVG={sum(values)/len(values):.2f}"
            )

            print(
                f"SELL DIST: "
                f"MIN={min(distances):.2f} | "
                f"MAX={max(distances):.2f} | "
                f"AVG={sum(distances)/len(distances):.2f}"
            )


if __name__ == "__main__":
    main()
