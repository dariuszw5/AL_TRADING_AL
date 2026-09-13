from src.data.data_provider import DataProvider
from src.analysis.market_analyzer import MarketAnalyzer
from src.strategy.basic_strategy import BasicStrategy


provider = DataProvider()

candles = provider.load_candles(
    "data/backtest/BTCUSDT_1m_5000.json"
)

analyzer = MarketAnalyzer(
    rsi_method="classic"
)

strategy = BasicStrategy()

history = []

signals = []
buy_count = 0
sell_count = 0
hold_count = 0

for candle in candles:
    history.append(candle)

    analysis = analyzer.analyze(history)

    sma_values = analysis["sma"]
    ema_values = analysis["ema"]
    rsi_values = analysis["rsi"]

    if not sma_values or not ema_values or not rsi_values:
        hold_count += 1
        continue

    sma_value = sma_values[-1]
    ema_value = ema_values[-1]
    rsi_value = rsi_values[-1]

    previous_ema = None

    if len(ema_values) >= 2:
        previous_ema = ema_values[-2]

    signal = strategy.generate_signal(
        sma_value=sma_value,
        ema_value=ema_value,
        rsi_value=rsi_value,
        min_difference=1.0,
        buy_rsi=30.0,
        sell_rsi=70.0,
        previous_ema=previous_ema
    )

    if signal == "BUY":
        buy_count += 1
        signals.append({
            "timestamp": candle.timestamp,
            "price": candle.close,
            "sma": sma_value,
            "ema": ema_value,
            "rsi": rsi_value,
            "difference": abs(ema_value - sma_value),
            "signal": signal
        })

    elif signal == "SELL":
        sell_count += 1
        signals.append({
            "timestamp": candle.timestamp,
            "price": candle.close,
            "sma": sma_value,
            "ema": ema_value,
            "rsi": rsi_value,
            "difference": abs(ema_value - sma_value),
            "signal": signal
        })

    else:
        hold_count += 1


print()
print("=== SIGNAL DIAGNOSTICS ===")
print()
print(f"Total candles: {len(candles)}")
print(f"BUY signals:   {buy_count}")
print(f"SELL signals:  {sell_count}")
print(f"HOLD:          {hold_count}")
print()

print("=== GENERATED SIGNALS ===")

for i, signal in enumerate(signals, 1):
    print()
    print(f"--- SIGNAL {i} ---")

    for key, value in signal.items():
        print(f"{key}: {value}")

print()
print("=== CONDITIONS ===")
print()
print("BUY:")
print("EMA > SMA")
print("RSI < 30")
print("Difference >= 1")
print()
print("SELL:")
print("EMA < SMA")
print("RSI > 70")
print("Difference >= 1")
