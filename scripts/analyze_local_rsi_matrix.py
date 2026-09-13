from src.backtest.backtest_runner import BacktestRunner


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALIDATION": "data/backtest/BTCUSDT_1m_validation_5000.json",
    "TEST": "data/backtest/BTCUSDT_1m_test_5000.json",
}

BUY_VALUES = [
    34.50,
    35.00,
    35.25,
    35.50,
    35.75,
    36.00,
]

SELL_VALUES = [
    68.00,
    68.25,
    68.50,
    68.75,
    69.00,
    69.25,
    69.50,
    69.75,
    70.00,
]

FEE = 0.0004
MIN_DIFFERENCE = 1.0


def run_strategy(data_file, buy_rsi, sell_rsi):

    runner = BacktestRunner(
        symbol="BTCUSDT",
        interval="1m",
        limit=5000,
        initial_balance=1000.0,
        buy_rsi=buy_rsi,
        sell_rsi=sell_rsi,
        min_difference=MIN_DIFFERENCE,
        trading_fee=FEE,
        rsi_method="classic",
        data_source="file",
        data_file=data_file,
    )

    runner.load_data()
    runner.run()

    result = runner.get_backtest_result()

    trades = result.trades

    profits = [
        float(trade["profit"])
        for trade in trades
    ]

    gross_wins = sum(
        p for p in profits
        if p > 0
    )

    gross_losses = sum(
        abs(p) for p in profits
        if p < 0
    )

    if gross_losses > 0:
        pf = gross_wins / gross_losses
    else:
        pf = float("inf") if gross_wins > 0 else 0.0

    wins = sum(
        1 for p in profits
        if p > 0
    )

    win_rate = (
        wins / len(profits) * 100.0
        if profits
        else 0.0
    )

    equity = result.equity_curve

    peak = equity[0]
    max_drawdown = 0.0

    for value in equity:

        if value > peak:
            peak = value

        drawdown = peak - value

        if drawdown > max_drawdown:
            max_drawdown = drawdown

    return {
        "profit": float(result.balance - result.initial_balance),
        "pf": pf,
        "dd": max_drawdown,
        "wr": win_rate,
        "trades": len(trades),
    }


def main():

    print()
    print("=" * 150)
    print("LOCAL BUY x SELL RSI MATRIX")
    print(
        "BUY=34.50..36.00 | "
        "SELL=68.00..70.00 | "
        f"FEE={FEE:.4f} | "
        f"MIN_DIFF={MIN_DIFFERENCE:.2f} | "
        "RSI=classic"
    )
    print("=" * 150)

    all_results = []

    total_runs = (
        len(BUY_VALUES)
        * len(SELL_VALUES)
        * len(DATASETS)
    )

    completed = 0

    for buy in BUY_VALUES:

        for sell in SELL_VALUES:

            row = {
                "buy": buy,
                "sell": sell,
            }

            for dataset, path in DATASETS.items():

                result = run_strategy(
                    path,
                    buy,
                    sell
                )

                row[dataset] = result

                completed += 1

                print(
                    f"[{completed:3d}/{total_runs}] "
                    f"BUY={buy:5.2f} "
                    f"SELL={sell:5.2f} "
                    f"{dataset:<12} "
                    f"PROFIT={result['profit']:+9.4f} "
                    f"PF={result['pf']:6.3f} "
                    f"DD={result['dd']:8.4f} "
                    f"TRADES={result['trades']:2d}"
                )

            profits = [
                row["TRAIN"]["profit"],
                row["VALIDATION"]["profit"],
                row["TEST"]["profit"],
            ]

            row["total"] = sum(profits)
            row["worst"] = min(profits)
            row["average"] = sum(profits) / 3.0
            row["positive_datasets"] = sum(
                1
                for p in profits
                if p > 0
            )

            row["min_pf"] = min(
                row["TRAIN"]["pf"],
                row["VALIDATION"]["pf"],
                row["TEST"]["pf"],
            )

            row["average_dd"] = (
                row["TRAIN"]["dd"]
                + row["VALIDATION"]["dd"]
                + row["TEST"]["dd"]
            ) / 3.0

            all_results.append(row)

    print()
    print("=" * 150)
    print("RANKING #1 — TOTAL PROFIT")
    print("=" * 150)

    ranked_total = sorted(
        all_results,
        key=lambda x: (
            x["total"],
            x["worst"],
            x["average"],
        ),
        reverse=True,
    )

    print(
        f"{'R':>3} | "
        f"{'BUY':>5} | "
        f"{'SELL':>5} | "
        f"{'TRAIN':>10} | "
        f"{'VALID':>10} | "
        f"{'TEST':>10} | "
        f"{'TOTAL':>10} | "
        f"{'WORST':>10} | "
        f"{'AVG':>10} | "
        f"{'+DATA':>5}"
    )

    print("-" * 150)

    for rank, row in enumerate(
        ranked_total[:20],
        start=1
    ):

        print(
            f"{rank:3d} | "
            f"{row['buy']:5.2f} | "
            f"{row['sell']:5.2f} | "
            f"{row['TRAIN']['profit']:+10.4f} | "
            f"{row['VALIDATION']['profit']:+10.4f} | "
            f"{row['TEST']['profit']:+10.4f} | "
            f"{row['total']:+10.4f} | "
            f"{row['worst']:+10.4f} | "
            f"{row['average']:+10.4f} | "
            f"{row['positive_datasets']:5d}"
        )

    print()
    print("=" * 150)
    print("RANKING #2 — WORST DATASET")
    print("=" * 150)

    ranked_worst = sorted(
        all_results,
        key=lambda x: (
            x["positive_datasets"],
            x["worst"],
            x["total"],
            x["average"],
        ),
        reverse=True,
    )

    print(
        f"{'R':>3} | "
        f"{'BUY':>5} | "
        f"{'SELL':>5} | "
        f"{'TRAIN':>10} | "
        f"{'VALID':>10} | "
        f"{'TEST':>10} | "
        f"{'TOTAL':>10} | "
        f"{'WORST':>10} | "
        f"{'AVG':>10} | "
        f"{'+DATA':>5}"
    )

    print("-" * 150)

    for rank, row in enumerate(
        ranked_worst[:20],
        start=1
    ):

        print(
            f"{rank:3d} | "
            f"{row['buy']:5.2f} | "
            f"{row['sell']:5.2f} | "
            f"{row['TRAIN']['profit']:+10.4f} | "
            f"{row['VALIDATION']['profit']:+10.4f} | "
            f"{row['TEST']['profit']:+10.4f} | "
            f"{row['total']:+10.4f} | "
            f"{row['worst']:+10.4f} | "
            f"{row['average']:+10.4f} | "
            f"{row['positive_datasets']:5d}"
        )

    print()
    print("=" * 150)
    print("ALL 3 DATASETS POSITIVE")
    print("=" * 150)

    robust = [
        row
        for row in all_results
        if row["positive_datasets"] == 3
    ]

    robust = sorted(
        robust,
        key=lambda x: (
            x["worst"],
            x["total"],
            x["average"],
        ),
        reverse=True,
    )

    print(
        f"FOUND: {len(robust)} / "
        f"{len(all_results)} combinations"
    )

    print()

    for rank, row in enumerate(
        robust[:30],
        start=1
    ):

        print(
            f"{rank:3d}. "
            f"BUY={row['buy']:5.2f} | "
            f"SELL={row['sell']:5.2f} | "
            f"TRAIN={row['TRAIN']['profit']:+9.4f} | "
            f"VALID={row['VALIDATION']['profit']:+9.4f} | "
            f"TEST={row['TEST']['profit']:+9.4f} | "
            f"TOTAL={row['total']:+9.4f} | "
            f"WORST={row['worst']:+9.4f}"
        )

    print()
    print("=" * 150)
    print("CANDIDATE NEIGHBORHOOD")
    print("=" * 150)

    candidate = next(
        row
        for row in all_results
        if (
            row["buy"] == 35.50
            and row["sell"] == 68.50
        )
    )

    print(
        "CANDIDATE BUY=35.50 SELL=68.50"
    )

    print(
        f"TRAIN={candidate['TRAIN']['profit']:+.4f} | "
        f"VALID={candidate['VALIDATION']['profit']:+.4f} | "
        f"TEST={candidate['TEST']['profit']:+.4f} | "
        f"TOTAL={candidate['total']:+.4f} | "
        f"WORST={candidate['worst']:+.4f}"
    )

    print()

    neighbors = []

    for row in all_results:

        buy_distance = abs(
            row["buy"] - 35.50
        )

        sell_distance = abs(
            row["sell"] - 68.50
        )

        if (
            buy_distance <= 0.50
            and sell_distance <= 0.50
            and not (
                row["buy"] == 35.50
                and row["sell"] == 68.50
            )
        ):
            neighbors.append(row)

    neighbors = sorted(
        neighbors,
        key=lambda x: (
            x["total"],
            x["worst"],
        ),
        reverse=True,
    )

    for row in neighbors:

        print(
            f"BUY={row['buy']:5.2f} | "
            f"SELL={row['sell']:5.2f} | "
            f"TRAIN={row['TRAIN']['profit']:+9.4f} | "
            f"VALID={row['VALIDATION']['profit']:+9.4f} | "
            f"TEST={row['TEST']['profit']:+9.4f} | "
            f"TOTAL={row['total']:+9.4f} | "
            f"WORST={row['worst']:+9.4f}"
        )

    print()
    print("=" * 150)
    print("MATRIX COMPLETE")
    print("=" * 150)


if __name__ == "__main__":
    main()
