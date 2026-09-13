from src.backtest.backtest_runner import BacktestRunner
import random
import statistics


DATASETS = {
    "OOS #1": "data/backtest/BTCUSDT_1m_forward_5000.json",
    "OOS #2": "data/backtest/BTCUSDT_1m_forward_5000_oos2.json",
}


def get_profits(data_file):
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

    return [
        float(trade.get("profit", 0.0))
        for trade in runner.get_trades()
    ]


def calculate_metrics(profits, initial_balance=1000.0):
    balance = initial_balance
    peak = initial_balance
    max_drawdown = 0.0

    for profit in profits:
        balance += profit

        if balance > peak:
            peak = balance

        drawdown = peak - balance

        if drawdown > max_drawdown:
            max_drawdown = drawdown

    return balance - initial_balance, max_drawdown


def bootstrap(profits, simulations=10000, seed=42):

    rng = random.Random(seed)

    n = len(profits)

    final_profits = []
    drawdowns = []

    for _ in range(simulations):

        sample = [
            rng.choice(profits)
            for _ in range(n)
        ]

        profit, max_drawdown = calculate_metrics(sample)

        final_profits.append(profit)
        drawdowns.append(max_drawdown)

    final_profits.sort()
    drawdowns.sort()

    negative = sum(1 for p in final_profits if p < 0)
    positive = sum(1 for p in final_profits if p > 0)
    flat = sum(1 for p in final_profits if p == 0)

    return {
        "mean_profit": statistics.mean(final_profits),
        "median_profit": statistics.median(final_profits),
        "p05_profit": final_profits[int(simulations * 0.05)],
        "p95_profit": final_profits[int(simulations * 0.95)],
        "worst_profit": final_profits[0],
        "best_profit": final_profits[-1],
        "mean_dd": statistics.mean(drawdowns),
        "median_dd": statistics.median(drawdowns),
        "p95_dd": drawdowns[int(simulations * 0.95)],
        "worst_dd": drawdowns[-1],
        "positive_pct": positive / simulations * 100,
        "negative_pct": negative / simulations * 100,
        "flat_pct": flat / simulations * 100,
    }


oos1 = get_profits(DATASETS["OOS #1"])
oos2 = get_profits(DATASETS["OOS #2"])
combined = oos1 + oos2


print()
print("=" * 120)
print("=== BOOTSTRAP | FROZEN STRATEGY | 10,000 SIMULATIONS ===")
print("=" * 120)
print("BUY=33.8 | SELL=68.5 | TIME=241 | RSI=classic | MIN_DIFF=1.0 | FEE=0.0004")
print()
print("Każda symulacja losuje N transakcji Z POWTÓRZENIAMI z rzeczywistego OOS.")
print("Nie jest to optymalizacja parametrów.")
print()


for name, profits in [
    ("OOS #1", oos1),
    ("OOS #2", oos2),
    ("OOS #1 + OOS #2", combined),
]:

    metrics = bootstrap(profits)

    actual_profit = sum(profits)
    actual_expectancy = statistics.mean(profits)

    print("=" * 120)
    print(f"=== {name} ===")
    print("=" * 120)

    print(f"Liczba transakcji       : {len(profits)}")
    print(f"Rzeczywisty profit      : {actual_profit:.4f}")
    print(f"Rzeczywista expectancy  : {actual_expectancy:.4f}")
    print()

    print(f"Średni profit bootstrap : {metrics['mean_profit']:.4f}")
    print(f"Mediana profit          : {metrics['median_profit']:.4f}")
    print(f"5 percentyl profit      : {metrics['p05_profit']:.4f}")
    print(f"95 percentyl profit     : {metrics['p95_profit']:.4f}")
    print(f"Najgorszy profit        : {metrics['worst_profit']:.4f}")
    print(f"Najlepszy profit        : {metrics['best_profit']:.4f}")
    print()

    print(f"Średni max DD           : {metrics['mean_dd']:.4f}")
    print(f"Mediana max DD          : {metrics['median_dd']:.4f}")
    print(f"95 percentyl max DD     : {metrics['p95_dd']:.4f}")
    print(f"Najgorszy max DD        : {metrics['worst_dd']:.4f}")
    print()

    print(f"Symulacje dodatnie      : {metrics['positive_pct']:.2f}%")
    print(f"Symulacje ujemne        : {metrics['negative_pct']:.2f}%")
    print(f"Symulacje flat          : {metrics['flat_pct']:.2f}%")
    print()


print("=" * 120)
print("END")
print("=" * 120)
