from src.backtest.backtest_runner import BacktestRunner


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALIDATION": "data/backtest/BTCUSDT_1m_validation_5000.json",
    "TEST": "data/backtest/BTCUSDT_1m_test_5000.json",
}


STRATEGIES = {
    "BASELINE": {
        "buy": 30.00,
        "sell": 70.00,
    },
    "CANDIDATE": {
        "buy": 35.50,
        "sell": 68.50,
    },
}


MIN_DIFFERENCE = 1.0
TRADING_FEE = 0.0004
RSI_METHOD = "classic"


def run_backtest(data_file, buy_rsi, sell_rsi):

    runner = BacktestRunner(
        symbol="BTCUSDT",
        interval="1m",
        limit=5000,
        initial_balance=1000.0,
        buy_rsi=buy_rsi,
        sell_rsi=sell_rsi,
        min_difference=MIN_DIFFERENCE,
        trading_fee=TRADING_FEE,
        rsi_method=RSI_METHOD,
        data_source="file",
        data_file=data_file,
    )

    runner.load_data()
    runner.run()

    return runner


def entry_index(trade, candles):

    timestamp = trade.get("entry_timestamp")

    for index, candle in enumerate(candles):

        if candle.timestamp == timestamp:
            return index

    return None


def build_equity(trades, candles):

    equity = 1000.0
    points = []

    for number, trade in enumerate(trades, start=1):

        profit = float(
            trade.get("profit", 0.0)
        )

        equity += profit

        index = entry_index(
            trade,
            candles
        )

        points.append({
            "number": number,
            "index": index,
            "side": trade.get(
                "side",
                trade.get("signal", "?")
            ),
            "profit": profit,
            "equity": equity,
        })

    return points


def print_trade_sequence(label, points):

    print()
    print(f"{label} TRADE SEQUENCE")
    print("-" * 115)

    print(
        f"{'#':>3} | "
        f"{'INDEX':>6} | "
        f"{'SIDE':>5} | "
        f"{'TRADE P/L':>12} | "
        f"{'EQUITY':>12}"
    )

    print("-" * 115)

    for point in points:

        print(
            f"{point['number']:3d} | "
            f"{str(point['index']):>6} | "
            f"{point['side']:>5} | "
            f"{point['profit']:+12.4f} | "
            f"{point['equity']:12.4f}"
        )


def compare_equity(name, path):

    baseline_runner = run_backtest(
        path,
        STRATEGIES["BASELINE"]["buy"],
        STRATEGIES["BASELINE"]["sell"],
    )

    candidate_runner = run_backtest(
        path,
        STRATEGIES["CANDIDATE"]["buy"],
        STRATEGIES["CANDIDATE"]["sell"],
    )

    candles = baseline_runner.candles

    baseline_points = build_equity(
        baseline_runner.get_trades(),
        candles,
    )

    candidate_points = build_equity(
        candidate_runner.get_trades(),
        candles,
    )

    print()
    print("=" * 130)
    print(
        f"{name} | EQUITY ANALYSIS | "
        f"FEE={TRADING_FEE:.4f}"
    )
    print("=" * 130)

    print()
    print(
        f"BASELINE  30/70     | "
        f"PROFIT={baseline_runner.get_total_profit():+.4f} | "
        f"FINAL={baseline_runner.get_balance():.4f} | "
        f"PF={baseline_runner.get_profit_factor():.4f} | "
        f"DD={baseline_runner.get_max_drawdown():.4f}"
    )

    print(
        f"CANDIDATE 35.50/68.50 | "
        f"PROFIT={candidate_runner.get_total_profit():+.4f} | "
        f"FINAL={candidate_runner.get_balance():.4f} | "
        f"PF={candidate_runner.get_profit_factor():.4f} | "
        f"DD={candidate_runner.get_max_drawdown():.4f}"
    )

    print()
    print(
        f"FINAL EQUITY ADVANTAGE: "
        f"{candidate_runner.get_balance() - baseline_runner.get_balance():+.4f}"
    )

    print_trade_sequence(
        "BASELINE",
        baseline_points
    )

    print_trade_sequence(
        "CANDIDATE",
        candidate_points
    )

    # Compare equity at each completed trade.
    # Since the two strategies can have different trade counts,
    # comparison is made by chronological candle index.

    events = []

    for point in baseline_points:

        events.append({
            "index": point["index"],
            "strategy": "BASELINE",
            "profit": point["profit"],
        })

    for point in candidate_points:

        events.append({
            "index": point["index"],
            "strategy": "CANDIDATE",
            "profit": point["profit"],
        })

    events.sort(
        key=lambda x: (
            x["index"] if x["index"] is not None else 999999,
            x["strategy"],
        )
    )

    baseline_equity = 1000.0
    candidate_equity = 1000.0

    max_advantage = None
    min_advantage = None
    max_advantage_event = None
    min_advantage_event = None

    first_candidate_ahead = None
    first_baseline_ahead = None

    print()
    print("=" * 130)
    print("CHRONOLOGICAL EQUITY DIVERGENCES")
    print("=" * 130)

    print()
    print(
        f"{'INDEX':>6} | "
        f"{'STRATEGY':>10} | "
        f"{'P/L':>12} | "
        f"{'BASE EQ':>12} | "
        f"{'CAND EQ':>12} | "
        f"{'ADVANTAGE':>12}"
    )

    print("-" * 130)

    for event in events:

        if event["strategy"] == "BASELINE":

            baseline_equity += event["profit"]

        else:

            candidate_equity += event["profit"]

        advantage = candidate_equity - baseline_equity

        print(
            f"{event['index']:6d} | "
            f"{event['strategy']:>10s} | "
            f"{event['profit']:+12.4f} | "
            f"{baseline_equity:12.4f} | "
            f"{candidate_equity:12.4f} | "
            f"{advantage:+12.4f}"
        )

        if (
            first_candidate_ahead is None
            and advantage > 0
        ):

            first_candidate_ahead = {
                "index": event["index"],
                "advantage": advantage,
            }

        if (
            first_baseline_ahead is None
            and advantage < 0
        ):

            first_baseline_ahead = {
                "index": event["index"],
                "advantage": advantage,
            }

        if (
            max_advantage is None
            or advantage > max_advantage
        ):

            max_advantage = advantage

            max_advantage_event = {
                "index": event["index"],
                "advantage": advantage,
            }

        if (
            min_advantage is None
            or advantage < min_advantage
        ):

            min_advantage = advantage

            min_advantage_event = {
                "index": event["index"],
                "advantage": advantage,
            }

    print()
    print("=" * 130)
    print("EQUITY SUMMARY")
    print("=" * 130)

    if first_candidate_ahead is not None:

        print(
            f"CANDIDATE FIRST AHEAD: "
            f"INDEX={first_candidate_ahead['index']} | "
            f"ADVANTAGE={first_candidate_ahead['advantage']:+.4f}"
        )

    else:

        print("CANDIDATE FIRST AHEAD: NEVER")

    if first_baseline_ahead is not None:

        print(
            f"BASELINE FIRST AHEAD: "
            f"INDEX={first_baseline_ahead['index']} | "
            f"ADVANTAGE={first_baseline_ahead['advantage']:+.4f}"
        )

    else:

        print("BASELINE FIRST AHEAD: NEVER")

    print(
        f"MAX CANDIDATE ADVANTAGE: "
        f"INDEX={max_advantage_event['index']} | "
        f"{max_advantage_event['advantage']:+.4f}"
    )

    print(
        f"MAX BASELINE ADVANTAGE: "
        f"INDEX={min_advantage_event['index']} | "
        f"{min_advantage_event['advantage']:+.4f}"
    )

    print(
        f"FINAL ADVANTAGE: "
        f"{candidate_runner.get_total_profit() - baseline_runner.get_total_profit():+.4f}"
    )


def main():

    print()
    print("=" * 130)
    print("BASELINE vs CANDIDATE — EQUITY ANALYSIS")
    print(
        f"BASELINE=30/70 | "
        f"CANDIDATE=35.50/68.50 | "
        f"FEE={TRADING_FEE:.4f} | "
        f"MIN_DIFF={MIN_DIFFERENCE:.2f} | "
        f"RSI={RSI_METHOD}"
    )
    print("=" * 130)

    for name, path in DATASETS.items():

        compare_equity(
            name,
            path
        )


if __name__ == "__main__":
    main()
