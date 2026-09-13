from src.backtest.backtest_runner import BacktestRunner


DATASETS = [
    ("OOS #1", "data/backtest/BTCUSDT_1m_forward_5000.json"),
    ("OOS #2", "data/backtest/BTCUSDT_1m_forward_5000_oos2.json"),
]


all_trades = []


for dataset_name, data_file in DATASETS:

    runner = BacktestRunner(
        symbol="BTCUSDT",
        interval="1m",
        limit=5000,
        initial_balance=1000.0,
        buy_rsi=33.8,
        sell_rsi=68.5,
        min_difference=1.0,
        trading_fee=0.0004,
        rsi_method="classic",
        data_source="file",
        data_file=data_file,
    )

    runner.agent.config.max_position_candles = 241

    runner.load_data()
    runner.run()

    for trade in runner.get_trades():

        all_trades.append({
            "dataset": dataset_name,
            "side": str(trade.get("side", "?")).upper(),
            "profit": float(trade.get("profit", 0.0)),
        })


def calculate_metrics(trades):

    profits = [trade["profit"] for trade in trades]

    wins = [p for p in profits if p > 0]
    losses = [p for p in profits if p < 0]

    total_profit = sum(profits)
    expectancy = total_profit / len(profits) if profits else 0.0

    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))

    if gross_loss > 0:
        profit_factor = gross_profit / gross_loss
    elif gross_profit > 0:
        profit_factor = float("inf")
    else:
        profit_factor = 0.0

    win_rate = (len(wins) / len(profits) * 100.0) if profits else 0.0

    return {
        "trades": len(profits),
        "wins": len(wins),
        "losses": len(losses),
        "profit": total_profit,
        "expectancy": expectancy,
        "pf": profit_factor,
        "win_rate": win_rate,
    }


WINDOWS = [5, 7, 10]


print()
print("=" * 125)
print("=== OOS #1 + OOS #2 | ROLLING EXPECTANCY + PROFIT FACTOR ===")
print("=" * 125)
print("BUY=33.8 | SELL=68.5 | TIME=241 | RSI=classic | MIN_DIFF=1.0 | FEE=0.0004")
print()
print("Chronological order: OOS #1 trade 1-14 -> OOS #2 trade 15-28")
print()


for window in WINDOWS:

    print()
    print("=" * 125)
    print(f"=== ROLLING WINDOW = {window} TRADES ===")
    print("=" * 125)

    print(
        f"{'RANGE':<10} | "
        f"{'DATASET':<7} | "
        f"{'W/L':<5} | "
        f"{'WR':>7} | "
        f"{'PROFIT':>10} | "
        f"{'EXPECT':>10} | "
        f"{'PF':>8}"
    )

    print("-" * 125)

    for end in range(window, len(all_trades) + 1):

        start = end - window
        subset = all_trades[start:end]

        metrics = calculate_metrics(subset)

        datasets = sorted(set(trade["dataset"] for trade in subset))

        if len(datasets) == 1:
            dataset_label = datasets[0]
        else:
            dataset_label = "MIXED"

        pf_text = (
            f"{metrics['pf']:.4f}"
            if metrics["pf"] != float("inf")
            else "INF"
        )

        print(
            f"{start + 1:02d}-{end:02d}     | "
            f"{dataset_label:<7} | "
            f"{metrics['wins']}/{metrics['losses']:<3} | "
            f"{metrics['win_rate']:>6.2f}% | "
            f"{metrics['profit']:>10.4f} | "
            f"{metrics['expectancy']:>10.4f} | "
            f"{pf_text:>8}"
        )


print()
print("=" * 125)
print("=== FULL OOS SUMMARY ===")
print("=" * 125)

full = calculate_metrics(all_trades)

print(f"Trades          : {full['trades']}")
print(f"Wins            : {full['wins']}")
print(f"Losses          : {full['losses']}")
print(f"Win rate        : {full['win_rate']:.2f}%")
print(f"Profit          : {full['profit']:.4f}")
print(f"Expectancy      : {full['expectancy']:.4f}")
print(f"Profit factor   : {full['pf']:.4f}")

print()
print("=" * 125)
print("END")
print("=" * 125)
