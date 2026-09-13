from src.agent.agent_engine import AgentEngine
from src.agent.agent_config import AgentConfig
from src.data.data_provider import DataProvider


CONFIG = AgentConfig(
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
    max_position_candles=240,
)


def pct_change(start, end):
    if start == 0:
        return 0.0

    return ((end - start) / start) * 100.0


class AnalysisAgent(AgentEngine):

    def __init__(self, config):
        super().__init__(config)

        self.entry_snapshots = []

    def _build_snapshot(
        self,
        candles,
        signal,
        entry_price
    ):
        if signal not in ("BUY", "SELL"):
            return None

        if len(candles) < 121:
            return None

        closes = [
            float(candle.close)
            for candle in candles
        ]

        analysis = self.strategy_engine.analyzer.analyze(
            candles
        )

        sma_values = analysis.get("sma", [])
        ema_values = analysis.get("ema", [])
        rsi_values = analysis.get("rsi", [])

        if not sma_values or not ema_values or not rsi_values:
            return None

        sma_value = float(sma_values[-1])
        ema_value = float(ema_values[-1])
        rsi_value = float(rsi_values[-1])

        current = closes[-1]

        momentum = {}

        for lookback in (5, 15, 30, 60, 120):
            previous = closes[-lookback - 1]

            momentum[lookback] = pct_change(
                previous,
                current
            )

        return {
            "side": signal,
            "entry_price": float(entry_price),
            "rsi": rsi_value,
            "ema": ema_value,
            "sma": sma_value,
            "ema_sma_diff": ema_value - sma_value,
            "momentum": momentum,
        }

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

        position = self.trading_engine.trade_manager.position

        if position is not None:

            candles = self.data_manager.get_all()

            snapshot = self._build_snapshot(
                candles=candles,
                signal=position["side"],
                entry_price=position["entry_price"]
            )

            if snapshot is not None:
                snapshot["entry_timestamp"] = (
                    position["entry_timestamp"]
                )

                self.entry_snapshots.append(snapshot)

        return result


def load_candles(path):
    provider = DataProvider()
    return provider.load_candles(path)


def favorable_move(side, entry_price, price):
    if side == "BUY":
        return pct_change(entry_price, price)

    return pct_change(price, entry_price)


def analyze_trade_path(
    candles,
    trade,
    intervals=(5, 10, 15, 30, 60, 120)
):
    side = trade["side"]
    entry_price = float(trade["entry_price"])
    entry_timestamp = trade["entry_timestamp"]
    exit_timestamp = trade["exit_timestamp"]

    path = [
        candle
        for candle in candles
        if (
            candle.timestamp >= entry_timestamp
            and candle.timestamp <= exit_timestamp
        )
    ]

    result = {
        interval: None
        for interval in intervals
    }

    if not path:
        return result

    entry_index = None

    for i, candle in enumerate(candles):
        if candle.timestamp == entry_timestamp:
            entry_index = i
            break

    if entry_index is None:
        return result

    for interval in intervals:

        target_index = entry_index + interval

        if target_index >= len(candles):
            continue

        target_candle = candles[target_index]

        if target_candle.timestamp > exit_timestamp:
            continue

        if side == "BUY":

            best = max(
                float(candle.high)
                for candle in candles[
                    entry_index + 1:
                    target_index + 1
                ]
            )

        else:

            best = min(
                float(candle.low)
                for candle in candles[
                    entry_index + 1:
                    target_index + 1
                ]
            )

        result[interval] = favorable_move(
            side,
            entry_price,
            best
        )

    return result


def threshold_time(
    candles,
    trade,
    threshold
):
    side = trade["side"]
    entry_price = float(trade["entry_price"])
    entry_timestamp = trade["entry_timestamp"]
    exit_timestamp = trade["exit_timestamp"]

    entry_index = None

    for i, candle in enumerate(candles):
        if candle.timestamp == entry_timestamp:
            entry_index = i
            break

    if entry_index is None:
        return None

    for offset in range(
        1,
        len(candles) - entry_index
    ):

        candle = candles[entry_index + offset]

        if candle.timestamp > exit_timestamp:
            break

        if side == "BUY":
            best_price = float(candle.high)
        else:
            best_price = float(candle.low)

        favorable = favorable_move(
            side,
            entry_price,
            best_price
        )

        if favorable >= threshold:
            return offset

    return None


def print_dataset(path):

    candles = load_candles(path)

    agent = AnalysisAgent(CONFIG)

    agent.run(candles)

    closed_trades = (
        agent.trading_engine
        .trade_manager
        .trade_history
    )

    print()
    print("=" * 130)
    print(path)
    print("=" * 130)

    print(
        f"Trades: {len(closed_trades)}"
    )

    if not closed_trades:
        print("No trades.")
        return

    print()
    print("MFE BY TIME")
    print("-" * 100)

    print(
        f"{'#':>3} "
        f"{'SIDE':>5} "
        f"{'PROFIT':>10} "
        f"{'5m':>8} "
        f"{'10m':>8} "
        f"{'15m':>8} "
        f"{'30m':>8} "
        f"{'60m':>8} "
        f"{'120m':>8}"
    )

    print("-" * 100)

    paths = []

    for i, trade in enumerate(closed_trades):

        mfe = analyze_trade_path(
            candles,
            trade
        )

        paths.append(mfe)

        def fmt(value):
            if value is None:
                return "N/A"
            return f"{value:.3f}%"

        print(
            f"{i + 1:3d} "
            f"{trade['side']:>5} "
            f"{float(trade['profit']):10.4f} "
            f"{fmt(mfe[5]):>8} "
            f"{fmt(mfe[10]):>8} "
            f"{fmt(mfe[15]):>8} "
            f"{fmt(mfe[30]):>8} "
            f"{fmt(mfe[60]):>8} "
            f"{fmt(mfe[120]):>8}"
        )

    print()
    print("TIME TO REACH FAVORABLE THRESHOLD")
    print("-" * 110)

    print(
        f"{'#':>3} "
        f"{'SIDE':>5} "
        f"{'PROFIT':>10} "
        f"{'+0.25%':>10} "
        f"{'+0.50%':>10} "
        f"{'+0.75%':>10} "
        f"{'+1.00%':>10}"
    )

    print("-" * 110)

    thresholds = (
        0.25,
        0.50,
        0.75,
        1.00
    )

    threshold_results = []

    for i, trade in enumerate(closed_trades):

        values = []

        for threshold in thresholds:

            value = threshold_time(
                candles,
                trade,
                threshold
            )

            values.append(value)

        threshold_results.append(values)

        def fmt_time(value):
            if value is None:
                return "N/A"
            return f"{value:>5}m"

        print(
            f"{i + 1:3d} "
            f"{trade['side']:>5} "
            f"{float(trade['profit']):10.4f} "
            f"{fmt_time(values[0]):>10} "
            f"{fmt_time(values[1]):>10} "
            f"{fmt_time(values[2]):>10} "
            f"{fmt_time(values[3]):>10}"
        )

    print()
    print("WIN vs LOSS — MFE AFTER TIME")
    print("-" * 110)

    for category, condition in (
        ("WIN", lambda trade: float(trade["profit"]) > 0),
        ("LOSS", lambda trade: float(trade["profit"]) < 0),
    ):

        selected = [
            (
                trade,
                paths[i]
            )
            for i, trade in enumerate(closed_trades)
            if condition(trade)
        ]

        if not selected:
            print(
                f"{category}: no trades"
            )
            continue

        print()
        print(
            f"{category} | N={len(selected)}"
        )

        for interval in (
            5,
            10,
            15,
            30,
            60,
            120
        ):

            values = [
                path[interval]
                for _, path in selected
                if path[interval] is not None
            ]

            if not values:
                print(
                    f"  {interval:3d}m | no data"
                )
                continue

            avg = sum(values) / len(values)

            reached_050 = sum(
                1
                for value in values
                if value >= 0.50
            )

            reached_100 = sum(
                1
                for value in values
                if value >= 1.00
            )

            print(
                f"  {interval:3d}m | "
                f"Avg MFE={avg:7.3f}% | "
                f">=0.50%={reached_050:2d}/{len(values)} | "
                f">=1.00%={reached_100:2d}/{len(values)}"
            )

    print()
    print("THRESHOLD HIT RATE — ALL TRADES")
    print("-" * 90)

    for threshold in thresholds:

        reached = 0

        for values in threshold_results:

            if values[thresholds.index(threshold)] is not None:
                reached += 1

        print(
            f"+{threshold:.2f}% | "
            f"Reached={reached:2d}/{len(closed_trades)} | "
            f"Rate={reached / len(closed_trades) * 100:6.2f}%"
        )


def main():

    print_dataset(
        "data/backtest/BTCUSDT_1m_5000.json"
    )

    print_dataset(
        "data/backtest/BTCUSDT_1m_validation_5000.json"
    )


if __name__ == "__main__":
    main()