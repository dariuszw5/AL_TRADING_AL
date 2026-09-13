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

print()
print("=" * 100)
print("=== OOS #1 | BUY vs SELL ===")
print("=" * 100)
print("BUY=33.8 | SELL=68.5 | TIME=241 | RSI=classic | FEE=0.0004")
print()


for side in ["BUY", "SELL"]:

    side_trades = [
        trade for trade in trades
        if str(trade.get("side", "")).upper() == side
    ]

    profits = [
        float(trade.get("profit", 0.0))
        for trade in side_trades
    ]

    wins = [p for p in profits if p > 0]
    losses = [p for p in profits if p < 0]

    total_profit = sum(profits)

    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))

    pf = (
        gross_profit / gross_loss
        if gross_loss > 0
        else float("inf")
    )

    win_rate = (
        len(wins) / len(profits) * 100.0
        if profits
        else 0.0
    )

    expectancy = (
        total_profit / len(profits)
        if profits
        else 0.0
    )

    sorted_profits = sorted(profits, reverse=True)

    top1 = sorted_profits[0] if sorted_profits else 0.0

    without_top1 = (
        total_profit - top1
        if sorted_profits
        else 0.0
    )

    print()
    print("-" * 100)
    print(f"{side}")
    print("-" * 100)

    print(f"Trades              : {len(profits)}")
    print(f"Winners             : {len(wins)}")
    print(f"Losers              : {len(losses)}")
    print(f"Win rate            : {win_rate:>10.2f}%")
    print(f"Total profit        : {total_profit:>10.4f}")
    print(f"Profit factor       : {pf:>10.4f}")
    print(f"Expectancy          : {expectancy:>10.4f}")
    print(f"Top winner          : {top1:>10.4f}")
    print(f"Profit without Top1 : {without_top1:>10.4f}")

    print()
    print("TRADE PROFITS")

    for i, profit in enumerate(sorted_profits, 1):
        print(f"{i:>2}. {profit:>10.4f}")


print()
print("=" * 100)
print("END")
print("=" * 100)
