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
print("=== OOS #1 | TRADE DICT KEYS ===")
print("=" * 100)

if not trades:
    print("NO TRADES")
else:
    print()
    print("NUMBER OF TRADES:", len(trades))

    print()
    print("KEYS:")
    for key in trades[0].keys():
        print(f"  {key!r}")

    print()
    print("FIRST TRADE:")
    print(trades[0])

print()
print("=" * 100)
print("END")
print("=" * 100)
