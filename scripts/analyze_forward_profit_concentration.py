from src.backtest.backtest_runner import BacktestRunner


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
    data_file="data/backtest/BTCUSDT_1m_forward_5000.json",
)

runner.agent.config.max_position_candles = 241

runner.load_data()
runner.run()

trades = runner.get_trades()

profits = [
    float(trade.get("profit", 0.0))
    for trade in trades
]

profits.sort(reverse=True)

total_profit = sum(profits)

print()
print("=" * 90)
print("=== OOS #1 PROFIT CONCENTRATION ===")
print("=" * 90)
print("BUY=33.8 | SELL=68.5 | TIME=241 | RSI=classic | FEE=0.0004")
print()

print(f"Trades              : {len(profits)}")
print(f"Total profit        : {total_profit:10.4f}")
print(f"Profit factor       : {runner.get_profit_factor():10.4f}")
print(f"Expectancy          : {runner.get_expectancy():10.4f}")

if not profits:
    raise SystemExit

print()
print("TOP WINNERS")
print("-" * 90)

for i, profit in enumerate(profits[:5], 1):
    share = (
        profit / total_profit * 100.0
        if total_profit != 0
        else 0.0
    )

    print(
        f"{i:>2}. Profit={profit:>10.4f} | "
        f"Share of total={share:>7.2f}%"
    )

top1 = sum(profits[:1])
top3 = sum(profits[:3])

remaining_after_top1 = total_profit - top1
remaining_after_top3 = total_profit - top3

print()
print("CONCENTRATION")
print("-" * 90)
print(f"Top 1 contribution        : {top1:>10.4f}")
print(f"Profit without Top 1      : {remaining_after_top1:>10.4f}")
print(f"Top 3 contribution        : {top3:>10.4f}")
print(f"Profit without Top 3      : {remaining_after_top3:>10.4f}")

if len(profits) >= 2:

    median_index = len(profits) // 2

    if len(profits) % 2:
        median_profit = profits[median_index]
    else:
        median_profit = (
            profits[median_index - 1]
            + profits[median_index]
        ) / 2.0

    print(f"Median trade profit       : {median_profit:>10.4f}")

print()
print("=" * 90)
print("END")
print("=" * 90)
