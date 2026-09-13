import json

from src.analysis.market_analyzer import MarketAnalyzer
from src.data.candle import Candle
from src.strategy.basic_strategy import BasicStrategy
from src.backtest.backtest_runner import BacktestRunner


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
        data = json.load(f)

    candles = []

    for item in data:
        if isinstance(item, dict):
            candles.append(
                Candle(
                    timestamp=item["timestamp"],
                    open=item["open"],
                    high=item["high"],
                    low=item["low"],
                    close=item["close"],
                    volume=item["volume"],
                )
            )

    return candles


def get_value(values, index):
    if index < 0 or index >= len(values):
        return None
    return values[index]


def analyze_signals(candles, sell_rsi):
    analyzer = MarketAnalyzer(rsi_method="classic")
    strategy = BasicStrategy()

    analysis = analyzer.analyze(candles)

    sma_values = analysis.get("sma", [])
    ema_values = analysis.get("ema", [])
    rsi_values = analysis.get("rsi", [])

    signals = {}

    for candle_index in range(len(candles)):
        sma_index = candle_index - 19
        ema_index = candle_index - 19
        rsi_index = candle_index - 14

        if (
            sma_index < 0
            or ema_index < 0
            or rsi_index < 0
            or sma_index >= len(sma_values)
            or ema_index >= len(ema_values)
            or rsi_index >= len(rsi_values)
        ):
            continue

        sma_value = sma_values[sma_index]
        ema_value = ema_values[ema_index]
        rsi_value = rsi_values[rsi_index]

        previous_ema = None

        if ema_index >= 1:
            previous_ema = ema_values[ema_index - 1]

        signal = strategy.generate_signal(
            sma_value=sma_value,
            ema_value=ema_value,
            rsi_value=rsi_value,
            min_difference=MIN_DIFFERENCE,
            buy_rsi=BUY_RSI,
            sell_rsi=sell_rsi,
            previous_ema=previous_ema,
        )

        signals[candle_index] = {
            "signal": signal,
            "sma": float(sma_value),
            "ema": float(ema_value),
            "rsi": float(rsi_value),
            "difference": abs(float(ema_value) - float(sma_value)),
            "timestamp": candles[candle_index].timestamp,
            "close": float(candles[candle_index].close),
        }

    return signals


def run_backtest(path, sell_rsi):
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


def trade_value(trade, *names):
    for name in names:
        if isinstance(trade, dict) and name in trade:
            return trade[name]

        if hasattr(trade, name):
            return getattr(trade, name)

    return None


def print_trade(index, trade):
    side = trade_value(trade, "side")

    entry_index = trade_value(
        trade,
        "entry_index",
        "entry_candle_index",
        "entry_bar",
    )

    exit_index = trade_value(
        trade,
        "exit_index",
        "exit_candle_index",
        "exit_bar",
    )

    entry_price = trade_value(trade, "entry_price", "entry")
    exit_price = trade_value(trade, "exit_price", "exit")
    profit = trade_value(trade, "profit", "pnl", "profit_loss")

    exit_reason = trade_value(
        trade,
        "exit_reason",
        "reason",
    )

    print(
        f"  #{index:02d} "
        f"{side:<4} "
        f"ENTRY={entry_index} "
        f"EXIT={exit_index} "
        f"PROFIT={profit:+.4f} "
        f"REASON={exit_reason}"
    )


def first_signal_divergence(signals_a, signals_b):
    common = sorted(
        set(signals_a.keys()) &
        set(signals_b.keys())
    )

    for index in common:
        a = signals_a[index]
        b = signals_b[index]

        if a["signal"] != b["signal"]:
            return index, a, b

    return None


def first_trade_divergence(trades_a, trades_b):
    count = min(len(trades_a), len(trades_b))

    for i in range(count):
        a = trades_a[i]
        b = trades_b[i]

        a_side = trade_value(a, "side")
        b_side = trade_value(b, "side")

        a_entry = trade_value(
            a,
            "entry_index",
            "entry_candle_index",
            "entry_bar",
        )

        b_entry = trade_value(
            b,
            "entry_index",
            "entry_candle_index",
            "entry_bar",
        )

        a_exit = trade_value(
            a,
            "exit_index",
            "exit_candle_index",
            "exit_bar",
        )

        b_exit = trade_value(
            b,
            "exit_index",
            "exit_candle_index",
            "exit_bar",
        )

        if (
            a_side != b_side
            or a_entry != b_entry
            or a_exit != b_exit
        ):
            return i + 1, a, b

    if len(trades_a) != len(trades_b):
        return count + 1, (
            trades_a[count]
            if count < len(trades_a)
            else None
        ), (
            trades_b[count]
            if count < len(trades_b)
            else None
        )

    return None


def main():
    for dataset_name, path in DATASETS.items():

        print()
        print("=" * 120)
        print(f"{dataset_name} | SELL {SELL_A:.2f} vs SELL {SELL_B:.2f}")
        print("=" * 120)

        candles = load_candles(path)

        signals_a = analyze_signals(candles, SELL_A)
        signals_b = analyze_signals(candles, SELL_B)

        signal_divergence = first_signal_divergence(
            signals_a,
            signals_b,
        )

        if signal_divergence is None:
            print()
            print("FIRST SIGNAL DIVERGENCE: NONE")
        else:
            index, a, b = signal_divergence

            print()
            print("FIRST SIGNAL DIVERGENCE")
            print("-" * 120)
            print(f"INDEX      = {index}")
            print(f"TIMESTAMP  = {a['timestamp']}")
            print(f"CLOSE      = {a['close']:.4f}")
            print(f"RSI        = {a['rsi']:.6f}")
            print(f"SMA        = {a['sma']:.6f}")
            print(f"EMA        = {a['ema']:.6f}")
            print(f"EMA-SMA    = {a['difference']:.6f}")
            print()
            print(f"SELL={SELL_A:.2f} SIGNAL = {a['signal']}")
            print(f"SELL={SELL_B:.2f} SIGNAL = {b['signal']}")

        runner_a = run_backtest(path, SELL_A)
        runner_b = run_backtest(path, SELL_B)

        trades_a = runner_a.backtest_engine.get_trades()
        trades_b = runner_b.backtest_engine.get_trades()

        trade_divergence = first_trade_divergence(
            trades_a,
            trades_b,
        )

        if trade_divergence is None:
            print()
            print("FIRST TRADE DIVERGENCE: NONE")
        else:
            trade_number, trade_a, trade_b = trade_divergence

            print()
            print("FIRST TRADE DIVERGENCE")
            print("-" * 120)
            print(f"TRADE NUMBER = #{trade_number:02d}")

            print()
            print(f"SELL={SELL_A:.2f}")
            if trade_a is None:
                print("  [NO TRADE]")
            else:
                print_trade(trade_number, trade_a)

            print()
            print(f"SELL={SELL_B:.2f}")
            if trade_b is None:
                print("  [NO TRADE]")
            else:
                print_trade(trade_number, trade_b)

        print()
        print("SUMMARY")
        print("-" * 120)

        print(
            f"SELL={SELL_A:.2f} | "
            f"TRADES={runner_a.backtest_engine.get_trade_count()} | "
            f"PROFIT={runner_a.backtest_engine.get_total_profit():+.4f} | "
            f"PF={runner_a.backtest_engine.get_profit_factor():.4f} | "
            f"DD={runner_a.backtest_engine.get_max_drawdown():.4f}"
        )

        print(
            f"SELL={SELL_B:.2f} | "
            f"TRADES={runner_b.backtest_engine.get_trade_count()} | "
            f"PROFIT={runner_b.backtest_engine.get_total_profit():+.4f} | "
            f"PF={runner_b.backtest_engine.get_profit_factor():.4f} | "
            f"DD={runner_b.backtest_engine.get_max_drawdown():.4f}"
        )

        print()
        print("TRADE SEQUENCES")
        print("-" * 120)

        print(f"SELL={SELL_A:.2f}")
        for i, trade in enumerate(trades_a, start=1):
            print_trade(i, trade)

        print()
        print(f"SELL={SELL_B:.2f}")
        for i, trade in enumerate(trades_b, start=1):
            print_trade(i, trade)


if __name__ == "__main__":
    main()
