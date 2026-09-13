from src.backtest.backtest_runner import BacktestRunner


runner = BacktestRunner(
    symbol="BTCUSDT",
    interval="1m",
    limit=5000,
    initial_balance=1000.0,
    buy_rsi=30.0,
    sell_rsi=70.0,
    min_difference=1.0,
    trading_fee=0.0,
    rsi_method="classic",
    data_source="file"
)

runner.load_data()
runner.run()

trades = runner.get_trades()

print()
print("=== TRADE DIAGNOSTICS ===")
print(f"Liczba transakcji: {len(trades)}")
print()

for i, trade in enumerate(trades, start=1):
    print(f"--- TRADE #{i} ---")

    if isinstance(trade, dict):
        for key, value in trade.items():
            print(f"{key}: {value}")
    else:
        print(trade)

    print()