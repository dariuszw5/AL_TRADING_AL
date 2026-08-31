from src.backtest.backtest_runner import BacktestRunner
from src.backtest.strategy_evaluator import StrategyEvaluator


def run_backtest(rsi_method):
    runner = BacktestRunner(
        symbol="BTCUSDT",
        interval="1m",
        limit=5000,
        initial_balance=1000.0,
        buy_rsi=30.0,
        sell_rsi=70.0,
        min_difference=1.0,
        trading_fee=0.001,
        rsi_method=rsi_method,
        data_source="file"
    )

    runner.load_data()
    runner.run()

    return runner.get_summary()


evaluator = StrategyEvaluator()

classic = run_backtest("classic")
wilder = run_backtest("wilder")

classic_score = evaluator.evaluate(classic)
wilder_score = evaluator.evaluate(wilder)


print()
print("=== RSI COMPARISON ===")
print()

print(f"{'Parametr':<20} {'Classic':>15} {'Wilder':>15}")
print("-" * 52)

print(
    f"{'Kapitał końcowy':<20} "
    f"{classic['final_balance']:>15.4f} "
    f"{wilder['final_balance']:>15.4f}"
)

print(
    f"{'Total profit':<20} "
    f"{classic['total_profit']:>15.4f} "
    f"{wilder['total_profit']:>15.4f}"
)

print(
    f"{'Transakcje':<20} "
    f"{classic['trades']:>15} "
    f"{wilder['trades']:>15}"
)

print(
    f"{'Wygrane':<20} "
    f"{classic['winning_trades']:>15} "
    f"{wilder['winning_trades']:>15}"
)

print(
    f"{'Przegrane':<20} "
    f"{classic['losing_trades']:>15} "
    f"{wilder['losing_trades']:>15}"
)

print(
    f"{'Win rate':<20} "
    f"{classic['win_rate']:>15.4f} "
    f"{wilder['win_rate']:>15.4f}"
)

print(
    f"{'Profit factor':<20} "
    f"{classic['profit_factor']:>15.4f} "
    f"{wilder['profit_factor']:>15.4f}"
)

print(
    f"{'Max drawdown':<20} "
    f"{classic['max_drawdown']:>15.4f} "
    f"{wilder['max_drawdown']:>15.4f}"
)

print(
    f"{'Expectancy':<20} "
    f"{classic['expectancy']:>15.4f} "
    f"{wilder['expectancy']:>15.4f}"
)

print(
    f"{'Strategy Score':<20} "
    f"{classic_score:>15.4f} "
    f"{wilder_score:>15.4f}"
)

print()

if classic_score > wilder_score:
    print("LEPSZA STRATEGIA: Classic RSI")
elif wilder_score > classic_score:
    print("LEPSZA STRATEGIA: Wilder RSI")
else:
    print("REMIS")

print()
print(
    f"Różnica zysku Wilder - Classic: "
    f"{wilder['total_profit'] - classic['total_profit']:.4f}"
)

print(
    f"Różnica score Wilder - Classic: "
    f"{wilder_score - classic_score:.4f}"
)