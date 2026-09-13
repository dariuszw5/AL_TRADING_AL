from src.backtest.backtest_runner import BacktestRunner


DATASETS = [
    ("OOS #1", "data/backtest/BTCUSDT_1m_forward_5000.json"),
    ("OOS #2", "data/backtest/BTCUSDT_1m_forward_5000_oos2.json"),
]


all_trades = []


for dataset_name, data_file in DATASETS:

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

    trades = runner.get_trades()

    for trade in trades:
        all_trades.append({
            "dataset": dataset_name,
            "side": str(trade.get("side", "?")).upper(),
            "profit": float(trade.get("profit", 0.0)),
            "exit_reason": str(trade.get("exit_reason", "?")),
        })


balance = 1000.0
peak = balance
max_drawdown = 0.0
max_drawdown_trade = 0

current_drawdown_start = None
current_drawdown_length = 0
max_drawdown_length = 0

last_peak_trade = 0
longest_recovery = 0

print()
print("=" * 125)
print("=== OOS #1 + OOS #2 | COMBINED EQUITY CURVE ===")
print("=" * 125)
print("BUY=33.8 | SELL=68.5 | TIME=241 | RSI=classic | MIN_DIFF=1.0 | FEE=0.0004")
print()

print(
    f"{'#':>3} | "
    f"{'DATASET':<7} | "
    f"{'SIDE':<5} | "
    f"{'RESULT':<5} | "
    f"{'PROFIT':>10} | "
    f"{'BALANCE':>11} | "
    f"{'PEAK':>11} | "
    f"{'DD':>10}"
)

print("-" * 125)


for i, trade in enumerate(all_trades, 1):

    profit = trade["profit"]

    balance += profit

    if balance > peak:

        peak = balance

        if current_drawdown_start is not None:
            recovery_length = i - current_drawdown_start

            if recovery_length > longest_recovery:
                longest_recovery = recovery_length

        current_drawdown_start = None

    drawdown = peak - balance

    if drawdown > 0:

        if current_drawdown_start is None:
            current_drawdown_start = i

        current_drawdown_length = i - current_drawdown_start + 1

        if current_drawdown_length > max_drawdown_length:
            max_drawdown_length = current_drawdown_length

    if drawdown > max_drawdown:
        max_drawdown = drawdown
        max_drawdown_trade = i

    result = "WIN" if profit > 0 else "LOSS" if profit < 0 else "FLAT"

    print(
        f"{i:>3} | "
        f"{trade['dataset']:<7} | "
        f"{trade['side']:<5} | "
        f"{result:<5} | "
        f"{profit:>10.4f} | "
        f"{balance:>11.4f} | "
        f"{peak:>11.4f} | "
        f"{drawdown:>10.4f}"
    )


if current_drawdown_start is not None:

    recovery_length = len(all_trades) - current_drawdown_start + 1

    if recovery_length > longest_recovery:
        longest_recovery = recovery_length


print()
print("=" * 125)
print("=== EQUITY SUMMARY ===")
print("=" * 125)

print(f"Initial balance             : {1000.0:.4f}")
print(f"Final balance               : {balance:.4f}")
print(f"Total profit                : {balance - 1000.0:.4f}")
print(f"Total trades                : {len(all_trades)}")
print(f"Max drawdown                : {max_drawdown:.4f}")
print(f"Trade of max drawdown       : {max_drawdown_trade}")
print(f"Longest drawdown duration   : {max_drawdown_length} trades")
print(f"Longest recovery             : {longest_recovery} trades")

print()
print("=" * 125)
print("END")
print("=" * 125)
