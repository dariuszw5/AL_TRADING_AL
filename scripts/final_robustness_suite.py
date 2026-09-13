import subprocess
import sys
from src.backtest.backtest_runner import BacktestRunner


PARAMS = {
    "symbol": "BTCUSDT",
    "interval": "1m",
    "limit": 5000,
    "initial_balance": 1000.0,
    "buy_rsi": 33.8,
    "sell_rsi": 68.5,
    "min_difference": 1.0,
    "trading_fee": 0.0004,
    "rsi_method": "classic",
    "max_position_candles": 241,
}


DATASETS = [
    ("TRAIN", "data/backtest/BTCUSDT_1m_5000.json"),
    ("VALIDATION", "data/backtest/BTCUSDT_1m_validation_5000.json"),
    ("TEST", "data/backtest/BTCUSDT_1m_test_5000.json"),
    ("OOS #1", "data/backtest/BTCUSDT_1m_forward_5000.json"),
    ("OOS #2", "data/backtest/BTCUSDT_1m_forward_5000_oos2.json"),
]


def run_dataset(name, path):

    runner = BacktestRunner(
        symbol=PARAMS["symbol"],
        interval=PARAMS["interval"],
        limit=PARAMS["limit"],
        initial_balance=PARAMS["initial_balance"],
        buy_rsi=PARAMS["buy_rsi"],
        sell_rsi=PARAMS["sell_rsi"],
        min_difference=PARAMS["min_difference"],
        trading_fee=PARAMS["trading_fee"],
        rsi_method=PARAMS["rsi_method"],
        data_source="file",
        data_file=path,
    )

    runner.agent.config.max_position_candles = PARAMS["max_position_candles"]

    runner.load_data()
    runner.run()

    trades = runner.get_trades()

    profits = [float(t.get("profit", 0.0)) for t in trades]

    wins = [p for p in profits if p > 0]
    losses = [p for p in profits if p < 0]

    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))

    pf = gross_profit / gross_loss if gross_loss > 0 else float("inf")
    profit = sum(profits)
    expectancy = profit / len(profits) if profits else 0.0
    win_rate = len(wins) / len(profits) * 100 if profits else 0.0

    buy = [t for t in trades if str(t.get("side", "")).upper() == "BUY"]
    sell = [t for t in trades if str(t.get("side", "")).upper() == "SELL"]

    def side_metrics(side_trades):

        side_profits = [
            float(t.get("profit", 0.0))
            for t in side_trades
        ]

        side_wins = [p for p in side_profits if p > 0]
        side_losses = [p for p in side_profits if p < 0]

        gp = sum(side_wins)
        gl = abs(sum(side_losses))

        side_pf = gp / gl if gl > 0 else (
            float("inf") if gp > 0 else 0.0
        )

        side_profit = sum(side_profits)

        return {
            "trades": len(side_profits),
            "wins": len(side_wins),
            "losses": len(side_losses),
            "profit": side_profit,
            "pf": side_pf,
            "expectancy": (
                side_profit / len(side_profits)
                if side_profits else 0.0
            ),
        }

    return {
        "name": name,
        "trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": win_rate,
        "profit": profit,
        "pf": pf,
        "expectancy": expectancy,
        "buy": side_metrics(buy),
        "sell": side_metrics(sell),
    }


print()
print("=" * 110)
print("=== FINAL ROBUSTNESS SUITE ===")
print("=" * 110)
print(
    "BUY=33.8 | SELL=68.5 | TIME=241 | "
    "RSI=classic | MIN_DIFF=1.0 | FEE=0.0004"
)
print()


results = []

for name, path in DATASETS:

    print(f"[1/3] Analysing {name} ...")

    result = run_dataset(name, path)
    results.append(result)

    print(
        f"      trades={result['trades']} | "
        f"WR={result['win_rate']:.2f}% | "
        f"profit={result['profit']:+.4f} | "
        f"PF={result['pf']:.4f}"
    )


print()
print("=" * 110)
print("=== TEST 1/3 | BUY vs SELL ===")
print("=" * 110)

for result in results:

    buy = result["buy"]
    sell = result["sell"]

    print()
    print(result["name"])
    print("-" * 110)

    print(
        f"BUY  | "
        f"{buy['trades']:>2} trades | "
        f"{buy['wins']}/{buy['losses']} | "
        f"profit={buy['profit']:+.4f} | "
        f"PF={buy['pf']:.4f} | "
        f"expectancy={buy['expectancy']:+.4f}"
    )

    print(
        f"SELL | "
        f"{sell['trades']:>2} trades | "
        f"{sell['wins']}/{sell['losses']} | "
        f"profit={sell['profit']:+.4f} | "
        f"PF={sell['pf']:.4f} | "
        f"expectancy={sell['expectancy']:+.4f}"
    )


oos_results = [
    r for r in results
    if r["name"] in ("OOS #1", "OOS #2")
]

oos_profit = sum(r["profit"] for r in oos_results)
oos_trades = sum(r["trades"] for r in oos_results)

oos_buy_profit = sum(r["buy"]["profit"] for r in oos_results)
oos_sell_profit = sum(r["sell"]["profit"] for r in oos_results)


print()
print("=" * 110)
print("=== TEST 2/3 | OOS STABILITY ===")
print("=" * 110)

print()
print(
    f"{'DATASET':<12} | "
    f"{'TRADES':>6} | "
    f"{'W/L':>5} | "
    f"{'WR':>7} | "
    f"{'PROFIT':>10} | "
    f"{'PF':>8} | "
    f"{'EXPECT':>9}"
)

print("-" * 110)

for result in results:

    print(
        f"{result['name']:<12} | "
        f"{result['trades']:>6} | "
        f"{result['wins']}/{result['losses']:<3} | "
        f"{result['win_rate']:>6.2f}% | "
        f"{result['profit']:>+10.4f} | "
        f"{result['pf']:>8.4f} | "
        f"{result['expectancy']:>+9.4f}"
    )


positive_datasets = sum(
    1 for r in results
    if r["profit"] > 0 and r["pf"] > 1.0
)

positive_oos = all(
    r["profit"] > 0 and r["pf"] > 1.0
    for r in oos_results
)


print()
print(f"Positive datasets        : {positive_datasets}/{len(results)}")
print(f"Positive OOS periods     : {sum(r['profit'] > 0 for r in oos_results)}/{len(oos_results)}")
print(f"Combined OOS trades      : {oos_trades}")
print(f"Combined OOS profit      : {oos_profit:+.4f}")
print(f"OOS BUY profit           : {oos_buy_profit:+.4f}")
print(f"OOS SELL profit          : {oos_sell_profit:+.4f}")


print()
print("=" * 110)
print("=== TEST 3/3 | FULL REGRESSION ===")
print("=" * 110)
print()
print("Running: python -m pytest -q")
print()

pytest_result = subprocess.run(
    [sys.executable, "-m", "pytest", "-q"],
    check=False,
)

pytest_passed = pytest_result.returncode == 0


print()
print("=" * 110)
print("=== FINAL FROZEN BENCHMARK ===")
print("=" * 110)
print()
print("Running: python -m scripts.final_frozen_comparison")
print()

benchmark_result = subprocess.run(
    [sys.executable, "-m", "scripts.final_frozen_comparison"],
    check=False,
)

benchmark_ok = benchmark_result.returncode == 0


print()
print("=" * 110)
print("=== FINAL ROBUSTNESS VERDICT ===")
print("=" * 110)

conditions = {
    "ALL_DATASETS_POSITIVE": positive_datasets == len(results),
    "ALL_OOS_POSITIVE": positive_oos,
    "COMBINED_OOS_POSITIVE": oos_profit > 0,
    "OOS_BUY_POSITIVE": oos_buy_profit > 0,
    "REGRESSION_TESTS_PASS": pytest_passed,
    "FINAL_BENCHMARK_OK": benchmark_ok,
}

for name, passed in conditions.items():

    status = "PASS" if passed else "FAIL"

    print(
        f"{status:<5} | {name}"
    )


all_pass = all(conditions.values())


print()

if all_pass:

    print("VERDICT: PASS")
    print()
    print(
        "Zamrozony kandydat przechodzi koncowy pakiet "
        "robustness/regression bez zmiany parametrow."
    )

else:

    print("VERDICT: CONDITIONAL / REVIEW")
    print()
    print(
        "Nie wszystkie kryteria przeszly. "
        "Nie zmieniamy parametrow automatycznie."
    )


print()
print("=" * 110)
print("=== END OF FINAL ROBUSTNESS SUITE ===")
print("=" * 110)
