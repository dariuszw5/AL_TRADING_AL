from src.backtest.backtest_runner import BacktestRunner


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALIDATION": "data/backtest/BTCUSDT_1m_validation_5000.json",
    "TEST": "data/backtest/BTCUSDT_1m_test_5000.json",
    "OOS #1": "data/backtest/BTCUSDT_1m_forward_5000.json",
    "OOS #2": "data/backtest/BTCUSDT_1m_forward_5000_oos2.json",
}


PARAMS = {
    "buy_rsi": 33.8,
    "sell_rsi": 68.5,
    "min_difference": 1.0,
    "trading_fee": 0.0004,
    "rsi_method": "classic",
    "max_position_candles": 241,
}


results = []


for name, data_file in DATASETS.items():

    runner = BacktestRunner(
        symbol="BTCUSDT",
        interval="1m",
        limit=5000,
        initial_balance=1000.0,
        buy_rsi=PARAMS["buy_rsi"],
        sell_rsi=PARAMS["sell_rsi"],
        min_difference=PARAMS["min_difference"],
        trading_fee=PARAMS["trading_fee"],
        rsi_method=PARAMS["rsi_method"],
        data_source="file",
        data_file=data_file,
    )

    runner.agent.config.max_position_candles = PARAMS["max_position_candles"]

    runner.load_data()
    runner.run()

    summary = runner.get_summary()

    results.append({
        "name": name,
        "candles": summary["candles"],
        "final_balance": float(summary["final_balance"]),
        "trades": int(summary["trades"]),
        "wins": int(summary["winning_trades"]),
        "losses": int(summary["losing_trades"]),
        "win_rate": float(summary["win_rate"]),
        "profit": float(summary["total_profit"]),
        "max_drawdown": float(summary["max_drawdown"]),
        "profit_factor": float(summary["profit_factor"]),
        "average_win": float(summary["average_win"]),
        "average_loss": float(summary["average_loss"]),
        "largest_win": float(summary["largest_win"]),
        "largest_loss": float(summary["largest_loss"]),
        "expectancy": float(summary["expectancy"]),
    })


print()
print("=" * 125)
print("=== FINAL FROZEN STRATEGY | TRAIN → VALIDATION → TEST → OOS #1 → OOS #2 ===")
print("=" * 125)
print(
    "BUY=33.8 | SELL=68.5 | TIME=241 | "
    "RSI=classic | MIN_DIFF=1.0 | FEE=0.0004"
)
print()

print(
    f"{'DATASET':<12} | "
    f"{'TRADES':>6} | "
    f"{'W/L':>7} | "
    f"{'WR':>7} | "
    f"{'PROFIT':>11} | "
    f"{'PF':>8} | "
    f"{'MAX DD':>11} | "
    f"{'EXPECT.':>10} | "
    f"{'FINAL':>11}"
)

print("-" * 125)

for result in results:

    wl = f"{result['wins']}/{result['losses']}"

    print(
        f"{result['name']:<12} | "
        f"{result['trades']:>6} | "
        f"{wl:>7} | "
        f"{result['win_rate']:>6.2f}% | "
        f"{result['profit']:>11.4f} | "
        f"{result['profit_factor']:>8.4f} | "
        f"{result['max_drawdown']:>11.4f} | "
        f"{result['expectancy']:>10.4f} | "
        f"{result['final_balance']:>11.4f}"
    )

print()

print("DETAILED RESULTS")
print("-" * 125)

for result in results:

    print()
    print(f"[{result['name']}]")
    print(f"  Candles       : {result['candles']}")
    print(f"  Trades        : {result['trades']}")
    print(f"  Wins          : {result['wins']}")
    print(f"  Losses        : {result['losses']}")
    print(f"  Win rate      : {result['win_rate']:.4f}%")
    print(f"  Profit        : {result['profit']:.10f}")
    print(f"  Final balance : {result['final_balance']:.10f}")
    print(f"  Max drawdown  : {result['max_drawdown']:.10f}")
    print(f"  Profit factor : {result['profit_factor']:.10f}")
    print(f"  Average win   : {result['average_win']:.10f}")
    print(f"  Average loss  : {result['average_loss']:.10f}")
    print(f"  Largest win   : {result['largest_win']:.10f}")
    print(f"  Largest loss  : {result['largest_loss']:.10f}")
    print(f"  Expectancy    : {result['expectancy']:.10f}")


print()
print("=" * 125)
print("END")
print("=" * 125)
