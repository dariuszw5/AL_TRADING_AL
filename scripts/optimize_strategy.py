from src.backtest.strategy_optimizer import StrategyOptimizer


optimizer = StrategyOptimizer()

results = optimizer.run()

print()
print("=== STRATEGY OPTIMIZATION ===")
print()
print(f"Liczba przetestowanych strategii: {len(results)}")
print()

print(
    f"{'Rank':<6}"
    f"{'Method':<10}"
    f"{'Buy RSI':>10}"
    f"{'Sell RSI':>10}"
    f"{'Difference':>12}"
    f"{'Trades':>10}"
    f"{'Profit':>12}"
    f"{'PF':>10}"
    f"{'Drawdown':>12}"
    f"{'Score':>12}"
)

print("-" * 94)

for index, result in enumerate(results, start=1):
    config = result.config
    summary = result.summary

    print(
        f"{index:<6}"
        f"{config.rsi_method:<10}"
        f"{config.buy_rsi:>10.1f}"
        f"{config.sell_rsi:>10.1f}"
        f"{config.min_difference:>12.1f}"
        f"{summary['trades']:>10}"
        f"{summary['total_profit']:>12.4f}"
        f"{summary['profit_factor']:>10.4f}"
        f"{summary['max_drawdown']:>12.4f}"
        f"{result.score:>12.4f}"
    )

print()

best = optimizer.get_best_result()

print("=== BEST STRATEGY ===")
print()

print(f"RSI method:      {best.config.rsi_method}")
print(f"Buy RSI:         {best.config.buy_rsi}")
print(f"Sell RSI:        {best.config.sell_rsi}")
print(f"Min difference:  {best.config.min_difference}")
print(f"Trading fee:     {best.config.trading_fee}")
print()
print(f"Trades:          {best.summary['trades']}")
print(f"Total profit:    {best.summary['total_profit']:.4f}")
print(f"Profit factor:   {best.summary['profit_factor']:.4f}")
print(f"Win rate:        {best.summary['win_rate']:.4f}")
print(f"Max drawdown:    {best.summary['max_drawdown']:.4f}")
print(f"Expectancy:      {best.summary['expectancy']:.4f}")
print(f"Strategy score:  {best.score:.4f}")