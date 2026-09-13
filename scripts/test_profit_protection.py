from src.agent.agent_engine import AgentEngine
from src.agent.agent_config import AgentConfig
from src.data.data_provider import DataProvider


TRAIN_FILE = "data/backtest/BTCUSDT_1m_5000.json"
VALIDATION_FILE = "data/backtest/BTCUSDT_1m_validation_5000.json"


THRESHOLDS = [0.25, 0.50, 0.75, 1.00]
GIVEBACKS = [0.10, 0.20, 0.30, 0.40, 0.50]


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
            self.entry_snapshots.append({
                "signal": signal,
                "entry_price": current_price,
                "entry_timestamp": current_timestamp
            })

        return result


def load_candles(path):
    provider = DataProvider()

    candles = provider.load_candles(path)

    return candles


def favorable_move(side, entry_price, candle):
    if side == "BUY":
        return ((candle.high - entry_price) / entry_price) * 100.0

    return ((entry_price - candle.low) / entry_price) * 100.0


def adverse_move(side, entry_price, candle):
    if side == "BUY":
        return ((candle.low - entry_price) / entry_price) * 100.0

    return ((entry_price - candle.high) / entry_price) * 100.0


def build_index(candles):
    return {
        candle.timestamp: index
        for index, candle in enumerate(candles)
    }


def analyze_trade(
    candles,
    trade,
    threshold,
    giveback
):
    timestamps = build_index(candles)

    entry_timestamp = trade["entry_timestamp"]
    exit_timestamp = trade["exit_timestamp"]

    if entry_timestamp not in timestamps:
        return None

    entry_index = timestamps[entry_timestamp]

    if exit_timestamp in timestamps:
        exit_index = timestamps[exit_timestamp]
    else:
        exit_index = len(candles) - 1

    if exit_index <= entry_index:
        return None

    entry_price = trade["entry_price"]
    side = trade["side"]

    peak_mfe = 0.0
    threshold_reached = False
    threshold_time = None
    protection_exit_index = None

    for index in range(entry_index + 1, exit_index + 1):

        candle = candles[index]

        mfe = favorable_move(
            side,
            entry_price,
            candle
        )

        if mfe > peak_mfe:
            peak_mfe = mfe

        if (
            not threshold_reached
            and peak_mfe >= threshold
        ):
            threshold_reached = True
            threshold_time = index - entry_index

        if threshold_reached:

            current_move = favorable_move(
                side,
                entry_price,
                candle
            )

            allowed_floor = peak_mfe - giveback

            if current_move <= allowed_floor:
                protection_exit_index = index
                break

    return {
        "original_profit": trade["profit"],
        "peak_mfe": peak_mfe,
        "threshold_reached": threshold_reached,
        "threshold_time": threshold_time,
        "protection_exit_index": protection_exit_index,
        "exit_index": exit_index,
        "side": side,
        "entry_price": entry_price
    }


def calculate_protected_profit(
    candles,
    trade,
    analysis
):
    if analysis is None:
        return None

    if analysis["protection_exit_index"] is None:
        return trade["profit"]

    exit_index = analysis["protection_exit_index"]
    exit_price = candles[exit_index].close

    entry_price = trade["entry_price"]
    quantity = trade["quantity"]

    if trade["side"] == "BUY":
        return (
            exit_price - entry_price
        ) * quantity

    return (
        entry_price - exit_price
    ) * quantity


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

    closed_trades = (
        agent.trading_engine
        .trade_manager
        .trade_history
    )

    return candles, closed_trades


def evaluate_rule(
    candles,
    trades,
    threshold,
    giveback
):
    original_profit = 0.0
    protected_profit = 0.0

    original_wins = 0
    protected_wins = 0

    original_losses = 0
    protected_losses = 0

    exits = 0

    max_drawdown = 0.0
    equity = 1000.0
    peak = equity

    for trade in trades:

        original = trade["profit"]

        analysis = analyze_trade(
            candles,
            trade,
            threshold,
            giveback
        )

        protected = calculate_protected_profit(
            candles,
            trade,
            analysis
        )

        if protected is None:
            protected = original

        original_profit += original
        protected_profit += protected

        if original > 0:
            original_wins += 1
        elif original < 0:
            original_losses += 1

        if protected > 0:
            protected_wins += 1
        elif protected < 0:
            protected_losses += 1

        if (
            analysis is not None
            and analysis["protection_exit_index"] is not None
        ):
            exits += 1

        equity += protected

        if equity > peak:
            peak = equity

        dd = peak - equity

        if dd > max_drawdown:
            max_drawdown = dd

    protected_trades = (
        protected_wins + protected_losses
    )

    if protected_trades:
        win_rate = (
            protected_wins /
            protected_trades
        ) * 100.0
    else:
        win_rate = 0.0

    return {
        "original_profit": original_profit,
        "protected_profit": protected_profit,
        "difference": (
            protected_profit -
            original_profit
        ),
        "wins": protected_wins,
        "losses": protected_losses,
        "win_rate": win_rate,
        "exits": exits,
        "drawdown": max_drawdown
    }


def print_results(
    name,
    candles,
    trades
):
    print()
    print("=" * 110)
    print(name)
    print("=" * 110)

    print(
        f"{'THRESH':>8} "
        f"{'GIVEBACK':>10} "
        f"{'PROFIT':>12} "
        f"{'DELTA':>12} "
        f"{'WR':>8} "
        f"{'EXITS':>8} "
        f"{'DD':>12}"
    )

    print("-" * 110)

    results = []

    for threshold in THRESHOLDS:

        for giveback in GIVEBACKS:

            result = evaluate_rule(
                candles,
                trades,
                threshold,
                giveback
            )

            results.append(
                (
                    result["protected_profit"],
                    threshold,
                    giveback,
                    result
                )
            )

            print(
                f"{threshold:>7.2f}% "
                f"{giveback:>9.2f}% "
                f"{result['protected_profit']:>12.4f} "
                f"{result['difference']:>12.4f} "
                f"{result['win_rate']:>7.2f}% "
                f"{result['exits']:>8} "
                f"{result['drawdown']:>12.4f}"
            )

    print()
    print("TOP 5")
    print("-" * 110)

    results.sort(
        key=lambda item: item[0],
        reverse=True
    )

    for rank, (
        profit,
        threshold,
        giveback,
        result
    ) in enumerate(results[:5], 1):

        print(
            f"{rank}. "
            f"THRESH={threshold:.2f}% "
            f"GIVEBACK={giveback:.2f}% "
            f"PROFIT={profit:.4f} "
            f"DELTA={result['difference']:.4f} "
            f"WR={result['win_rate']:.2f}% "
            f"EXITS={result['exits']} "
            f"DD={result['drawdown']:.4f}"
        )


def main():

    datasets = [
        (
            "TRAIN",
            TRAIN_FILE
        ),
        (
            "VALIDATION",
            VALIDATION_FILE
        )
    ]

    for name, path in datasets:

        candles, trades = run_dataset(path)

        print_results(
            name,
            candles,
            trades
        )


if __name__ == "__main__":
    main()