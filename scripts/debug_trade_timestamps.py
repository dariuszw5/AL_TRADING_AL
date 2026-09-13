from pathlib import Path

from src.data.data_provider import DataProvider
from src.analysis.indicators import rsi
from src.backtest.backtest_runner import BacktestRunner


DATASETS = [
    (
        "OOS #1",
        Path("data/backtest/BTCUSDT_1m_forward_5000.json"),
    ),
    (
        "OOS #2",
        Path("data/backtest/BTCUSDT_1m_forward_5000_oos2.json"),
    ),
]


def value(candle, key):
    if isinstance(candle, dict):
        return candle[key]
    return getattr(candle, key)


for name, path in DATASETS:
    print()
    print("=" * 110)
    print(name)
    print("=" * 110)

    provider = DataProvider()
    candles = provider.load_candles(str(path))

    timestamps = [
        value(c, "timestamp")
        for c in candles
    ]

    closes = [
        float(value(c, "close"))
        for c in candles
    ]

    # Najważniejsze: pokazujemy również długość i typ timestampów.
    print(
        f"Candles={len(candles)} | "
        f"first_ts={timestamps[0]} | "
        f"last_ts={timestamps[-1]}"
    )

    runner = BacktestRunner(
        symbol="BTCUSDT",
        interval="1m",
        limit=100,
        initial_balance=1000.0,
        buy_rsi=33.8,
        sell_rsi=68.5,
        min_difference=1.0,
        trading_fee=0.0004,
        rsi_method="classic",
        risk_percent=5.0,
        max_daily_loss_percent=10.0,
        risk_reward_ratio=2.0,
        data_source="file",
        data_file=str(path),
    )

    runner.run()

    trades = runner.get_trades()

    print(f"Backtest trades={len(trades)}")
    print()
    print(
        f"{'#':>3} | {'SIDE':<6} | "
        f"{'ENTRY TS':>16} | {'EXIT TS':>16} | "
        f"{'PROFIT':>10} | {'EXIT':<12}"
    )
    print("-" * 110)

    for i, trade in enumerate(trades, 1):
        signal = trade.get("signal")
        entry_ts = trade.get("entry_timestamp")
        exit_ts = trade.get("exit_timestamp")
        profit = trade.get("profit", 0.0)
        exit_reason = trade.get("exit_reason", "N/A")

        print(
            f"{i:3d} | "
            f"{str(signal):<6} | "
            f"{str(entry_ts):>16} | "
            f"{str(exit_ts):>16} | "
            f"{float(profit):+10.4f} | "
            f"{str(exit_reason):<12}"
        )

    print()
    print("RAW FIRST TRADE:")
    if trades:
        print(trades[0])

print()
print("=" * 110)
print("KONIEC")
print("=" * 110)
