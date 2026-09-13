from src.backtest.backtest_runner import BacktestRunner

runner = BacktestRunner(
    symbol="BTCUSDT",
    interval="1m",
    limit=5000,
    initial_balance=1000.0,
    buy_rsi=29.50,
    sell_rsi=70.0,
    min_difference=1.0,
    trading_fee=0.0,
    rsi_method="classic",
    data_file="data/backtest/BTCUSDT_1m_test_5000.json",
)

result = runner.run()

print("TYPE:", type(result))
print("LENGTH:", len(result))
print("FIRST ELEMENT:", result[0] if result else None)
print("LAST ELEMENT:", result[-1] if result else None)
