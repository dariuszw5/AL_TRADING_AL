from src.backtest.backtest_runner import BacktestRunner


runner = BacktestRunner(
    symbol="BTCUSDT",
    interval="1m",
    limit=5000,
    initial_balance=1000.0,
    buy_rsi=34.10,
    sell_rsi=68.50,
    min_difference=1.0,
    trading_fee=0.0004,
    rsi_method="classic",
    data_source="file",
    data_file="data/backtest/BTCUSDT_1m_validation_5000.json",
)

runner.load_data()
runner.run()

result = runner.get_backtest_result()


def describe(obj, name):
    print()
    print("=" * 100)
    print(name)
    print("=" * 100)
    print("TYPE:", type(obj))

    if hasattr(obj, "__dict__"):
        print("\n__dict__ KEYS:")
        for key, value in obj.__dict__.items():
            print(
                f"  {key:<30} "
                f"type={type(value).__name__:<25} "
                f"len={len(value) if hasattr(value, '__len__') and not isinstance(value, (str, bytes)) else '-'}"
            )

    print("\nPUBLIC ATTRIBUTES:")
    for name in dir(obj):
        if name.startswith("_"):
            continue

        try:
            value = getattr(obj, name)
        except Exception:
            continue

        if callable(value):
            continue

        if isinstance(value, (str, int, float, bool, type(None))):
            print(f"  {name:<30} {value!r}")
        else:
            try:
                length = len(value)
            except Exception:
                length = "-"

            print(
                f"  {name:<30} "
                f"type={type(value).__name__:<25} "
                f"len={length}"
            )


describe(result, "BACKTEST RESULT")
describe(runner, "BACKTEST RUNNER")


print()
print("=" * 100)
print("POSSIBLE DATA HOLDERS")
print("=" * 100)

candidates = [
    "data",
    "candles",
    "history",
    "market_data",
    "data_manager",
    "agent",
    "agent_engine",
    "backtest_engine",
    "engine",
    "result",
    "backtest_result",
]

for name in candidates:
    if hasattr(runner, name):
        value = getattr(runner, name)
        print(
            f"runner.{name:<20} "
            f"type={type(value).__name__:<30} "
            f"len={len(value) if hasattr(value, '__len__') else '-'}"
        )

    if hasattr(result, name):
        value = getattr(result, name)
        print(
            f"result.{name:<20} "
            f"type={type(value).__name__:<30} "
            f"len={len(value) if hasattr(value, '__len__') else '-'}"
        )


print()
print("=" * 100)
print("FIRST TRADE")
print("=" * 100)

if result.trades:
    trade = result.trades[0]
    print("TYPE:", type(trade))

    if hasattr(trade, "__dict__"):
        for key, value in trade.__dict__.items():
            print(f"{key} = {value!r}")

    elif isinstance(trade, dict):
        for key, value in trade.items():
            print(f"{key} = {value!r}")

    else:
        print(repr(trade))


print()
print("=" * 100)
print("END")
print("=" * 100)
