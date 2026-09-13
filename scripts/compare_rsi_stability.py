from src.data.data_provider import DataProvider
from src.backtest.backtest_runner import BacktestRunner


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALIDATION": "data/backtest/BTCUSDT_1m_validation_5000.json",
    "TEST": "data/backtest/BTCUSDT_1m_test_5000.json",
}


RSI_VALUES = [
    34.50,
    34.75,
    35.00,
    35.25,
    35.50,
    35.75,
    36.00,
]


BASE_RSI = 34.50


def run_backtest(path, buy_rsi):
    runner = BacktestRunner(
        symbol="BTCUSDT",
        interval="1m",
        limit=5000,
        initial_balance=1000.0,
        buy_rsi=buy_rsi,
        sell_rsi=70.0,
        min_difference=1.0,
        trading_fee=0.0,
        rsi_method="classic",
        data_source="file",
        data_file=path,
    )

    runner.load_data()
    runner.run()

    return runner


def get_index_from_timestamp(data, timestamp):
    for i, candle in enumerate(data):
        if candle.timestamp == timestamp:
            return i

    return None


def get_trade_signature(trade, data):
    entry_index = get_index_from_timestamp(
        data,
        trade.get("entry_timestamp")
    )

    exit_index = get_index_from_timestamp(
        data,
        trade.get("exit_timestamp")
    )

    return (
        entry_index,
        exit_index,
        trade.get("entry_price"),
        trade.get("exit_price"),
        trade.get("profit"),
    )


def compare_with_base(base_runner, runner, data):
    base_trades = (
        base_runner.backtest_engine.get_trades()
    )

    trades = (
        runner.backtest_engine.get_trades()
    )

    changed = 0
    identical = 0

    common = min(
        len(base_trades),
        len(trades)
    )

    for i in range(common):
        base_signature = get_trade_signature(
            base_trades[i],
            data
        )

        signature = get_trade_signature(
            trades[i],
            data
        )

        if base_signature == signature:
            identical += 1
        else:
            changed += 1

    extra = max(
        0,
        len(trades) - len(base_trades)
    )

    missing = max(
        0,
        len(base_trades) - len(trades)
    )

    changed += extra
    changed += missing

    return {
        "identical": identical,
        "changed": changed,
        "extra": extra,
        "missing": missing,
    }


def print_trade_changes(base_runner, runner, data):
    base_trades = (
        base_runner.backtest_engine.get_trades()
    )

    trades = (
        runner.backtest_engine.get_trades()
    )

    common = min(
        len(base_trades),
        len(trades)
    )

    for i in range(common):
        base = base_trades[i]
        current = trades[i]

        base_signature = get_trade_signature(
            base,
            data
        )

        current_signature = get_trade_signature(
            current,
            data
        )

        if base_signature == current_signature:
            continue

        base_entry = get_index_from_timestamp(
            data,
            base.get("entry_timestamp")
        )

        current_entry = get_index_from_timestamp(
            data,
            current.get("entry_timestamp")
        )

        base_exit = get_index_from_timestamp(
            data,
            base.get("exit_timestamp")
        )

        current_exit = get_index_from_timestamp(
            data,
            current.get("exit_timestamp")
        )

        base_profit = base.get("profit")
        current_profit = current.get("profit")

        print(
            f"  SLOT #{i + 1:2d} | "
            f"BASE ENTRY={str(base_entry):>4} | "
            f"NEW ENTRY={str(current_entry):>4} | "
            f"BASE EXIT={str(base_exit):>4} | "
            f"NEW EXIT={str(current_exit):>4} | "
            f"BASE PROFIT={base_profit:+.4f} | "
            f"NEW PROFIT={current_profit:+.4f} | "
            f"DELTA={current_profit - base_profit:+.4f}"
        )

    if len(trades) > len(base_trades):
        for i in range(len(base_trades), len(trades)):
            trade = trades[i]

            entry = get_index_from_timestamp(
                data,
                trade.get("entry_timestamp")
            )

            exit_index = get_index_from_timestamp(
                data,
                trade.get("exit_timestamp")
            )

            print(
                f"  NEW TRADE #{i + 1:2d} | "
                f"ENTRY={str(entry):>4} | "
                f"EXIT={str(exit_index):>4} | "
                f"PROFIT={trade.get('profit'):+.4f}"
            )

    if len(trades) < len(base_trades):
        for i in range(len(trades), len(base_trades)):
            trade = base_trades[i]

            entry = get_index_from_timestamp(
                data,
                trade.get("entry_timestamp")
            )

            exit_index = get_index_from_timestamp(
                data,
                trade.get("exit_timestamp")
            )

            print(
                f"  MISSING TRADE #{i + 1:2d} | "
                f"ENTRY={str(entry):>4} | "
                f"EXIT={str(exit_index):>4} | "
                f"PROFIT={trade.get('profit'):+.4f}"
            )


def main():
    provider = DataProvider()

    all_results = {}

    for dataset_name, path in DATASETS.items():

        print()
        print("#" * 150)
        print(
            f"{dataset_name} | "
            f"BUY RSI STABILITY TEST"
        )
        print("#" * 150)

        data = provider.load_candles(path)

        base_runner = run_backtest(
            path,
            BASE_RSI
        )

        dataset_results = {}

        for buy_rsi in RSI_VALUES:

            runner = run_backtest(
                path,
                buy_rsi
            )

            engine = runner.backtest_engine

            comparison = compare_with_base(
                base_runner,
                runner,
                data
            )

            result = {
                "trades": engine.get_trade_count(),
                "profit": engine.get_total_profit(),
                "pf": engine.get_profit_factor(),
                "dd": engine.get_max_drawdown(),
                "win_rate": engine.get_win_rate(),
                "expectancy": engine.get_expectancy(),
                "comparison": comparison,
                "runner": runner,
            }

            dataset_results[buy_rsi] = result

        all_results[dataset_name] = dataset_results

        print()
        print(
            "RSI      TRADES      PROFIT        PF        DD        "
            "WR        EXP      CHANGED"
        )
        print("-" * 100)

        for buy_rsi in RSI_VALUES:

            result = dataset_results[buy_rsi]
            comparison = result["comparison"]

            print(
                f"{buy_rsi:5.2f}    "
                f"{result['trades']:5d}    "
                f"{result['profit']:+10.4f}    "
                f"{result['pf']:7.4f}    "
                f"{result['dd']:8.4f}    "
                f"{result['win_rate']:6.2f}%    "
                f"{result['expectancy']:+8.4f}    "
                f"{comparison['changed']:3d}"
            )

        print()
        print("=" * 150)
        print(
            f"{dataset_name} | "
            f"CHANGES RELATIVE TO BUY RSI {BASE_RSI:.2f}"
        )
        print("=" * 150)

        for buy_rsi in RSI_VALUES:

            if buy_rsi == BASE_RSI:
                continue

            result = dataset_results[buy_rsi]
            comparison = result["comparison"]

            print()
            print(
                f"BUY RSI {buy_rsi:.2f} | "
                f"PROFIT DELTA="
                f"{result['profit'] - dataset_results[BASE_RSI]['profit']:+.4f} | "
                f"PF DELTA="
                f"{result['pf'] - dataset_results[BASE_RSI]['pf']:+.4f} | "
                f"TRADES DELTA="
                f"{result['trades'] - dataset_results[BASE_RSI]['trades']:+d}"
            )

            print(
                f"IDENTICAL={comparison['identical']} | "
                f"CHANGED={comparison['changed']} | "
                f"EXTRA={comparison['extra']} | "
                f"MISSING={comparison['missing']}"
            )

            print_trade_changes(
                base_runner,
                result["runner"],
                data
            )

    print()
    print("#" * 150)
    print("CROSS-DATASET SUMMARY")
    print("#" * 150)

    print()
    print(
        "RSI      "
        "TRAIN PROFIT    "
        "VALID PROFIT   "
        "TEST PROFIT    "
        "TRAIN PF   "
        "VALID PF   "
        "TEST PF"
    )
    print("-" * 110)

    for buy_rsi in RSI_VALUES:

        train = all_results["TRAIN"][buy_rsi]
        validation = all_results["VALIDATION"][buy_rsi]
        test = all_results["TEST"][buy_rsi]

        print(
            f"{buy_rsi:5.2f}    "
            f"{train['profit']:+11.4f}    "
            f"{validation['profit']:+11.4f}    "
            f"{test['profit']:+11.4f}    "
            f"{train['pf']:8.4f}   "
            f"{validation['pf']:8.4f}   "
            f"{test['pf']:8.4f}"
        )


if __name__ == "__main__":
    main()
