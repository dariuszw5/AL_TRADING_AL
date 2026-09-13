from pathlib import Path

from src.backtest.backtest_runner import BacktestRunner


BUY_RSI = 33.8
SELL_RSI = 68.5
FEE = 0.0004
MIN_DIFF = 1.0

TIMES = list(range(235, 246))

DATASETS = [
    ("TRAIN", Path("data/backtest/BTCUSDT_1m_5000.json")),
    ("VALID", Path("data/backtest/BTCUSDT_1m_validation_5000.json")),
    ("TEST", Path("data/backtest/BTCUSDT_1m_test_5000.json")),
    ("OOS1", Path("data/backtest/BTCUSDT_1m_forward_5000.json")),
    ("OOS2", Path("data/backtest/BTCUSDT_1m_forward_5000_oos2.json")),
]


def run(path, time_exit):
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

    profits = [
        float(t.get("profit", 0.0))
        for t in trades
    ]

    gross_profit = sum(p for p in profits if p > 0)
    gross_loss = sum(abs(p) for p in profits if p < 0)

    pf = gross_profit / gross_loss if gross_loss else float("inf")

    return {
        "trades": len(trades),
        "profit": sum(profits),
        "pf": pf,
    }


results = {}

print()
print("=" * 125)
print("LOCAL TIME STABILITY | 235..245")
print("=" * 125)
print(
    f"BUY={BUY_RSI} | SELL={SELL_RSI} | "
    f"RSI=classic | MIN_DIFF={MIN_DIFF} | FEE={FEE}"
)
print()

for time_exit in TIMES:
    row = {}

    for name, path in DATASETS:
        row[name] = run(path, time_exit)

    results[time_exit] = row

    train = row["TRAIN"]
    valid = row["VALID"]
    test = row["TEST"]
    oos1 = row["OOS1"]
    oos2 = row["OOS2"]

    pre_oos_profit = (
        train["profit"]
        + valid["profit"]
        + test["profit"]
    )

    pre_oos_pf = (
        train["pf"]
        + valid["pf"]
        + test["pf"]
    ) / 3.0

    oos_profit = oos1["profit"] + oos2["profit"]

    print(
        f"TIME={time_exit:3d} | "
        f"TRAIN {train['profit']:+8.4f} PF={train['pf']:.3f} | "
        f"VALID {valid['profit']:+8.4f} PF={valid['pf']:.3f} | "
        f"TEST {test['profit']:+8.4f} PF={test['pf']:.3f} | "
        f"PRE-OOS {pre_oos_profit:+9.4f} | "
        f"OOS {oos_profit:+8.4f}"
    )

print()
print("=" * 125)
print("LOCAL STABILITY RANKING | TRAIN + VALID + TEST")
print("=" * 125)

ranking = []

for time_exit in TIMES:
    row = results[time_exit]

    train = row["TRAIN"]
    valid = row["VALID"]
    test = row["TEST"]

    profits = [
        train["profit"],
        valid["profit"],
        test["profit"],
    ]

    pfs = [
        train["pf"],
        valid["pf"],
        test["pf"],
    ]

    positive_datasets = sum(
        1 for p in profits if p > 0
    )

    min_profit = min(profits)
    total_profit = sum(profits)
    avg_pf = sum(pfs) / 3.0

    ranking.append(
        (
            positive_datasets,
            min_profit,
            total_profit,
            avg_pf,
            time_exit,
        )
    )

ranking.sort(
    key=lambda x: (
        -x[0],
        -x[1],
        -x[2],
        -x[3],
    )
)

print(
    f"{'TIME':>6} | "
    f"{'POS':>3} | "
    f"{'MIN PROFIT':>11} | "
    f"{'TOTAL PROFIT':>12} | "
    f"{'AVG PF':>7}"
)

print("-" * 125)

for positive, min_profit, total_profit, avg_pf, time_exit in ranking:
    print(
        f"{time_exit:6d} | "
        f"{positive:3d}/3 | "
        f"{min_profit:+11.4f} | "
        f"{total_profit:+12.4f} | "
        f"{avg_pf:7.3f}"
    )

print()
print("=" * 125)
print("OOS CONTROL — NIE UŻYWAMY DO WYBORU")
print("=" * 125)

for time_exit in TIMES:
    row = results[time_exit]

    oos1 = row["OOS1"]
    oos2 = row["OOS2"]

    print(
        f"TIME={time_exit:3d} | "
        f"OOS1={oos1['profit']:+8.4f} PF={oos1['pf']:.3f} | "
        f"OOS2={oos2['profit']:+8.4f} PF={oos2['pf']:.3f} | "
        f"COMBINED={oos1['profit'] + oos2['profit']:+9.4f}"
    )

print()
print("=" * 125)
print("KONIEC LOCAL TIME STABILITY")
print("=" * 125)
