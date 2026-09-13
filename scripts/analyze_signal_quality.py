from src.backtest.backtest_runner import BacktestRunner
from src.analysis.market_analyzer import MarketAnalyzer
from src.strategy.basic_strategy import BasicStrategy


FORWARD_WINDOWS = [30, 60, 120, 240]


def analyze_file(name, data_file):
    runner = BacktestRunner(
        symbol="BTCUSDT",
        interval="1m",
        limit=5000,
        initial_balance=1000.0,
        buy_rsi=30.0,
        sell_rsi=70.0,
        min_difference=1.0,
        trading_fee=0.0,
        rsi_method="classic",
        risk_percent=5.0,
        max_daily_loss_percent=10.0,
        risk_reward_ratio=2.0,
        data_source="file",
        data_file=data_file,
    )

    candles = runner.load_data()

    analyzer = MarketAnalyzer(rsi_method="classic")
    strategy = BasicStrategy()

    signals = []

    for i in range(len(candles)):
        history = candles[:i + 1]

        analysis = analyzer.analyze(history)

        sma_values = analysis.get("sma", [])
        ema_values = analysis.get("ema", [])
        rsi_values = analysis.get("rsi", [])

        if not sma_values or not ema_values or not rsi_values:
            continue

        sma_value = sma_values[-1]
        ema_value = ema_values[-1]
        rsi_value = rsi_values[-1]

        signal = strategy.generate_signal(
            sma_value=sma_value,
            ema_value=ema_value,
            rsi_value=rsi_value,
            min_difference=1.0,
            buy_rsi=30.0,
            sell_rsi=70.0,
        )

        if signal not in ("BUY", "SELL"):
            continue

        entry_price = candles[i].close

        row = {
            "index": i,
            "timestamp": candles[i].timestamp,
            "signal": signal,
            "entry": entry_price,
            "sma": sma_value,
            "ema": ema_value,
            "rsi": rsi_value,
            "difference": abs(ema_value - sma_value),
        }

        for minutes in FORWARD_WINDOWS:
            future_index = i + minutes

            if future_index >= len(candles):
                row[f"ret_{minutes}"] = None
                continue

            future_price = candles[future_index].close

            if signal == "BUY":
                ret = ((future_price - entry_price) / entry_price) * 100
            else:
                ret = ((entry_price - future_price) / entry_price) * 100

            row[f"ret_{minutes}"] = ret

        signals.append(row)

    print()
    print("=" * 90)
    print(f"{name}")
    print("=" * 90)
    print(f"SYGNAŁY: {len(signals)}")

    if not signals:
        print("Brak sygnałów.")
        return

    for minutes in FORWARD_WINDOWS:
        values = [
            x[f"ret_{minutes}"]
            for x in signals
            if x[f"ret_{minutes}"] is not None
        ]

        if not values:
            continue

        wins = [x for x in values if x > 0]
        losses = [x for x in values if x < 0]

        avg = sum(values) / len(values)
        win_rate = len(wins) / len(values) * 100

        gross_profit = sum(wins)
        gross_loss = abs(sum(losses))

        if gross_loss == 0:
            pf = float("inf") if gross_profit > 0 else 0.0
        else:
            pf = gross_profit / gross_loss

        print(
            f"{minutes:>4} min | "
            f"N={len(values):>3} | "
            f"WR={win_rate:>6.2f}% | "
            f"AVG={avg:>8.4f}% | "
            f"PF={pf:>7.3f} | "
            f"SUM={sum(values):>9.4f}%"
        )

    print()
    print("--- BUY / SELL ---")

    for signal_type in ("BUY", "SELL"):
        subset = [x for x in signals if x["signal"] == signal_type]

        print()
        print(f"{signal_type}: {len(subset)} sygnałów")

        for minutes in FORWARD_WINDOWS:
            values = [
                x[f"ret_{minutes}"]
                for x in subset
                if x[f"ret_{minutes}"] is not None
            ]

            if not values:
                continue

            wins = [x for x in values if x > 0]
            avg = sum(values) / len(values)
            win_rate = len(wins) / len(values) * 100

            print(
                f"  {minutes:>4} min | "
                f"WR={win_rate:>6.2f}% | "
                f"AVG={avg:>8.4f}% | "
                f"SUM={sum(values):>9.4f}%"
            )

    print()
    print("--- PIERWSZE SYGNAŁY ---")

    for n, signal in enumerate(signals[:20], start=1):
        print(
            f"{n:>2}. "
            f"{signal['timestamp']} | "
            f"{signal['signal']:>4} | "
            f"ENTRY={signal['entry']:.2f} | "
            f"RSI={signal['rsi']:.2f} | "
            f"EMA-SMA={signal['ema'] - signal['sma']:.2f} | "
            f"30m={signal['ret_30'] if signal['ret_30'] is not None else '---':>8} | "
            f"60m={signal['ret_60'] if signal['ret_60'] is not None else '---':>8} | "
            f"120m={signal['ret_120'] if signal['ret_120'] is not None else '---':>8} | "
            f"240m={signal['ret_240'] if signal['ret_240'] is not None else '---':>8}"
        )


if __name__ == "__main__":
    analyze_file(
        "TRAIN",
        "data/backtest/BTCUSDT_1m_5000.json"
    )

    analyze_file(
        "VALIDATION",
        "data/backtest/BTCUSDT_1m_validation_5000.json"
    )

