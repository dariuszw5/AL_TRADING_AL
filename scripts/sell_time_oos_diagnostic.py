from pathlib import Path

from src.backtest.backtest_runner import BacktestRunner


BUY_RSI = 33.8
SELL_RSI = 68.5
FEE = 0.0004
MIN_DIFF = 1.0

TIMES = [180, 200, 220, 240, 241, 260, 280, 300]

DATASETS = [
    ("TRAIN", Path("data/backtest/BTCUSDT_1m_5000.json")),
    ("VALID", Path("data/backtest/BTCUSDT_1m_validation_5000.json")),
    ("TEST", Path("data/backtest/BTCUSDT_1m_test_5000.json")),
    ("OOS1", Path("data/backtest/BTCUSDT_1m_forward_5000.json")),
    ("OOS2", Path("data/backtest/BTCUSDT_1m_forward_5000_oos2.json")),
]


def run_backtest(path, time_exit):
    runner = BacktestRunner(
        symbol="BTCUSDT",
        interval="1m",
        limit=100,
        initial_balance=1000.0,
        buy_rsi=BUY_RSI,
        sell_rsi=SELL_RSI,
        min_difference=MIN_DIFF,
        trading_fee=FEE,
        rsi_method="classic",
        risk_percent=5.0,
        max_daily_loss_percent=10.0,
        risk_reward_ratio=2.0,
        data_source="file",
        data_file=str(path),
    )

    runner.agent.config.max_position_candles = time_exit

    runner.run()

    trades = runner.get_trades()

    total_profit = sum(
        float(t.get("profit", 0.0))
        for t in trades
    )

    gross_profit = sum(
        float(t.get("profit", 0.0))
        for t in trades
        if float(t.get("profit", 0.0)) > 0
    )

    gross_loss = sum(
        abs(float(t.get("profit", 0.0)))
        for t in trades
        if float(t.get("profit", 0.0)) < 0
    )

    pf = (
        gross_profit / gross_loss
        if gross_loss > 0
        else float("inf")
    )

    sell_trades = [
        t for t in trades
        if t.get("side") == "SELL"
    ]

    sell_profit = sum(
        float(t.get("profit", 0.0))
        for t in sell_trades
    )

    sell_wins = sum(
        1
        for t in sell_trades
        if float(t.get("profit", 0.0)) > 0
    )

    sell_losses = len(sell_trades) - sell_wins

    sell_gross_profit = sum(
        float(t.get("profit", 0.0))
        for t in sell_trades
        if float(t.get("profit", 0.0)) > 0
    )

    sell_gross_loss = sum(
        abs(float(t.get("profit", 0.0)))
        for t in sell_trades
        if float(t.get("profit", 0.0)) < 0
    )

    sell_pf = (
        sell_gross_profit / sell_gross_loss
        if sell_gross_loss > 0
        else float("inf")
    )

    return {
        "trades": len(trades),
        "profit": total_profit,
        "pf": pf,
        "sell_trades": len(sell_trades),
        "sell_wins": sell_wins,
        "sell_losses": sell_losses,
        "sell_profit": sell_profit,
        "sell_pf": sell_pf,
    }


all_results = {}

print()
print("=" * 125)
print("SELL x TIME DIAGNOSTIC")
print("=" * 125)
print(
    f"BUY={BUY_RSI} | SELL={SELL_RSI} | "
    f"RSI=classic | MIN_DIFF={MIN_DIFF} | FEE={FEE}"
)
print()

for time_exit in TIMES:
    print()
    print("-" * 125)
    print(f"TIME = {time_exit}")
    print("-" * 125)

    row = {}

    for name, path in DATASETS:
        result = run_backtest(path, time_exit)
        row[name] = result

        print(
            f"{name:5s} | "
            f"ALL P={result['profit']:+8.4f} "
            f"PF={result['pf']:5.3f} | "
            f"SELL={result['sell_trades']:2d} "
            f"W/L={result['sell_wins']}/{result['sell_losses']} "
            f"P={result['sell_profit']:+8.4f} "
            f"PF={result['sell_pf']:5.3f}"
        )

    oos_profit = (
        row["OOS1"]["profit"]
        + row["OOS2"]["profit"]
    )

    oos_sell_profit = (
        row["OOS1"]["sell_profit"]
        + row["OOS2"]["sell_profit"]
    )

    oos_trades = (
        row["OOS1"]["trades"]
        + row["OOS2"]["trades"]
    )

    oos_sell_trades = (
        row["OOS1"]["sell_trades"]
        + row["OOS2"]["sell_trades"]
    )

    print()
    print(
        f"OOS COMBINED | "
        f"ALL trades={oos_trades:2d} "
        f"profit={oos_profit:+.4f} | "
        f"SELL trades={oos_sell_trades:2d} "
        f"profit={oos_sell_profit:+.4f}"
    )

    all_results[time_exit] = row


print()
print("=" * 125)
print("SUMMARY | OOS SELL x TIME")
print("=" * 125)

print(
    f"{'TIME':>6} | "
    f"{'OOS1 SELL':>12} | "
    f"{'OOS2 SELL':>12} | "
    f"{'OOS COMBINED':>15} | "
    f"{'OOS ALL':>12}"
)

print("-" * 125)

for time_exit in TIMES:
    row = all_results[time_exit]

    oos1 = row["OOS1"]["sell_profit"]
    oos2 = row["OOS2"]["sell_profit"]

    combined_sell = oos1 + oos2

    combined_all = (
        row["OOS1"]["profit"]
        + row["OOS2"]["profit"]
    )

    print(
        f"{time_exit:6d} | "
        f"{oos1:+12.4f} | "
        f"{oos2:+12.4f} | "
        f"{combined_sell:+15.4f} | "
        f"{combined_all:+12.4f}"
    )


print()
print("=" * 125)
print("KONIEC SELL x TIME")
print("=" * 125)
