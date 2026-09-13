from src.agent.agent_engine import AgentEngine
from src.agent.agent_config import AgentConfig
from src.data.data_provider import DataProvider


DATASETS = [
    (
        "TRAIN",
        "data/backtest/BTCUSDT_1m_5000.json"
    ),
    (
        "VALIDATION",
        "data/backtest/BTCUSDT_1m_validation_5000.json"
    )
]


class AnalysisAgent(AgentEngine):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.entry_snapshots = []

    def _open_signal_from_candle(
        self,
        signal,
        current_price,
        current_timestamp
    ):
        result = super()._open_signal_from_candle(
            signal=signal,
            current_price=current_price,
            current_timestamp=current_timestamp
        )

        if result is not None and result.get("position") is not None:

            analysis = self.strategy_engine.analyzer.analyze(
                self.data_manager.get_all()
            )

            sma = analysis.get("sma", [])
            ema = analysis.get("ema", [])
            rsi = analysis.get("rsi", [])

            if sma and ema and rsi:

                self.entry_snapshots.append({
                    "signal": signal,
                    "timestamp": current_timestamp,
                    "rsi": rsi[-1],
                    "difference": ema[-1] - sma[-1],
                })

        return result


def load_candles(path):
    provider = DataProvider()
    return provider.load_candles(path)


def run_dataset(path):

    candles = load_candles(path)

    config = AgentConfig(
        symbol="BTCUSDT",
        interval="1m",
        limit=100,
        risk_percent=5.0,
        stop_loss_percent=5.0,
        max_daily_loss_percent=10.0,
        max_exposure_percent=100.0,
        risk_reward_ratio=2.0,
        initial_balance=1000.0,
        buy_rsi=30.0,
        sell_rsi=70.0,
        min_difference=1.0,
        trading_fee=0.0,
        rsi_method="classic",
        max_position_candles=240
    )

    agent = AnalysisAgent(config=config)

    agent.run(candles)

    trades = (
        agent.trading_engine
        .trade_manager
        .trade_history
    )

    return candles, agent.entry_snapshots, trades


def build_trade_map(trades):

    return {
        trade["entry_timestamp"]: trade
        for trade in trades
    }


def print_trades(name, snapshots, trades):

    trade_map = build_trade_map(trades)

    print()
    print("=" * 120)
    print(name)
    print("=" * 120)

    print(
        f"{'#':>3} "
        f"{'SIDE':>6} "
        f"{'PROFIT':>10} "
        f"{'RSI':>8} "
        f"{'DIFF':>10} "
        f"{'RSI DIST':>10} "
        f"{'DIFF ABS':>10}"
    )

    print("-" * 120)

    rows = []

    for index, snapshot in enumerate(snapshots, 1):

        trade = trade_map.get(
            snapshot["timestamp"]
        )

        if trade is None:
            continue

        rsi = snapshot["rsi"]
        difference = snapshot["difference"]

        if snapshot["signal"] == "BUY":
            rsi_distance = 30.0 - rsi
        else:
            rsi_distance = rsi - 70.0

        rows.append({
            "side": snapshot["signal"],
            "profit": trade["profit"],
            "rsi": rsi,
            "difference": difference,
            "rsi_distance": rsi_distance,
            "difference_abs": abs(difference)
        })

        print(
            f"{index:>3} "
            f"{snapshot['signal']:>6} "
            f"{trade['profit']:>10.4f} "
            f"{rsi:>8.2f} "
            f"{difference:>10.3f} "
            f"{rsi_distance:>10.3f} "
            f"{abs(difference):>10.3f}"
        )

    return rows


def avg(values):

    if not values:
        return 0.0

    return sum(values) / len(values)


def print_group(name, rows):

    wins = [
        row for row in rows
        if row["profit"] > 0
    ]

    losses = [
        row for row in rows
        if row["profit"] < 0
    ]

    print()
    print(name)

    print(
        f"  WIN  | N={len(wins):>2} | "
        f"RSI={avg([x['rsi'] for x in wins]):>7.2f} | "
        f"DIFF={avg([x['difference'] for x in wins]):>8.3f} | "
        f"RSI_DIST={avg([x['rsi_distance'] for x in wins]):>7.3f} | "
        f"ABS_DIFF={avg([x['difference_abs'] for x in wins]):>7.3f}"
    )

    print(
        f"  LOSS | N={len(losses):>2} | "
        f"RSI={avg([x['rsi'] for x in losses]):>7.2f} | "
        f"DIFF={avg([x['difference'] for x in losses]):>8.3f} | "
        f"RSI_DIST={avg([x['rsi_distance'] for x in losses]):>7.3f} | "
        f"ABS_DIFF={avg([x['difference_abs'] for x in losses]):>7.3f}"
    )


def test_filters(rows):

    filters = [
        (
            "RSI extreme",
            lambda x: x["rsi_distance"] >= 3.0
        ),
        (
            "RSI extreme 5",
            lambda x: x["rsi_distance"] >= 5.0
        ),
        (
            "RSI extreme 8",
            lambda x: x["rsi_distance"] >= 8.0
        ),
        (
            "ABS DIFF >= 3",
            lambda x: x["difference_abs"] >= 3.0
        ),
        (
            "ABS DIFF >= 5",
            lambda x: x["difference_abs"] >= 5.0
        ),
        (
            "ABS DIFF >= 8",
            lambda x: x["difference_abs"] >= 8.0
        ),
        (
            "RSI >= 3 AND DIFF >= 3",
            lambda x: (
                x["rsi_distance"] >= 3.0
                and x["difference_abs"] >= 3.0
            )
        ),
        (
            "RSI >= 5 AND DIFF >= 3",
            lambda x: (
                x["rsi_distance"] >= 5.0
                and x["difference_abs"] >= 3.0
            )
        ),
        (
            "RSI >= 5 AND DIFF >= 5",
            lambda x: (
                x["rsi_distance"] >= 5.0
                and x["difference_abs"] >= 5.0
            )
        ),
    ]

    print()
    print("FILTER TEST")
    print("-" * 120)

    for name, condition in filters:

        selected = [
            row for row in rows
            if condition(row)
        ]

        wins = sum(
            1
            for row in selected
            if row["profit"] > 0
        )

        losses = sum(
            1
            for row in selected
            if row["profit"] < 0
        )

        profit = sum(
            row["profit"]
            for row in selected
        )

        if losses:
            pf = (
                sum(
                    row["profit"]
                    for row in selected
                    if row["profit"] > 0
                )
                /
                abs(
                    sum(
                        row["profit"]
                        for row in selected
                        if row["profit"] < 0
                    )
                )
            )
        else:
            pf = float("inf") if wins else 0.0

        if selected:
            wr = wins / len(selected) * 100.0
        else:
            wr = 0.0

        print(
            f"{name:<32} "
            f"N={len(selected):>2} "
            f"WR={wr:>7.2f}% "
            f"Profit={profit:>10.4f} "
            f"PF={pf:>7.3f}"
        )


def main():

    all_rows = {}

    for name, path in DATASETS:

        candles, snapshots, trades = run_dataset(path)

        rows = print_trades(
            name,
            snapshots,
            trades
        )

        all_rows[name] = rows

        print_group(
            "WIN vs LOSS",
            rows
        )

        test_filters(rows)

    print()
    print("=" * 120)
    print("CROSS-DATASET FILTER CHECK")
    print("=" * 120)

    train = all_rows["TRAIN"]
    validation = all_rows["VALIDATION"]

    filters = [
        (
            "RSI extreme >= 3",
            lambda x: x["rsi_distance"] >= 3.0
        ),
        (
            "RSI extreme >= 5",
            lambda x: x["rsi_distance"] >= 5.0
        ),
        (
            "RSI extreme >= 8",
            lambda x: x["rsi_distance"] >= 8.0
        ),
        (
            "ABS DIFF >= 3",
            lambda x: x["difference_abs"] >= 3.0
        ),
        (
            "ABS DIFF >= 5",
            lambda x: x["difference_abs"] >= 5.0
        ),
        (
            "ABS DIFF >= 8",
            lambda x: x["difference_abs"] >= 8.0
        ),
        (
            "RSI >= 3 AND DIFF >= 3",
            lambda x: (
                x["rsi_distance"] >= 3.0
                and x["difference_abs"] >= 3.0
            )
        ),
        (
            "RSI >= 5 AND DIFF >= 3",
            lambda x: (
                x["rsi_distance"] >= 5.0
                and x["difference_abs"] >= 3.0
            )
        ),
        (
            "RSI >= 5 AND DIFF >= 5",
            lambda x: (
                x["rsi_distance"] >= 5.0
                and x["difference_abs"] >= 5.0
            )
        ),
    ]

    for name, condition in filters:

        print()
        print(name)

        for dataset_name, rows in (
            ("TRAIN", train),
            ("VALIDATION", validation)
        ):

            selected = [
                row for row in rows
                if condition(row)
            ]

            wins = sum(
                1 for row in selected
                if row["profit"] > 0
            )

            losses = sum(
                1 for row in selected
                if row["profit"] < 0
            )

            profit = sum(
                row["profit"]
                for row in selected
            )

            if losses:
                pf = (
                    sum(
                        row["profit"]
                        for row in selected
                        if row["profit"] > 0
                    )
                    /
                    abs(
                        sum(
                            row["profit"]
                            for row in selected
                            if row["profit"] < 0
                        )
                    )
                )
            else:
                pf = float("inf") if wins else 0.0

            wr = (
                wins / len(selected) * 100.0
                if selected
                else 0.0
            )

            print(
                f"  {dataset_name:<10} "
                f"N={len(selected):>2} "
                f"WR={wr:>7.2f}% "
                f"Profit={profit:>10.4f} "
                f"PF={pf:>7.3f}"
            )


if __name__ == "__main__":
    main()