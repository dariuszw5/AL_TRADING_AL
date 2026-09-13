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

DIFF_THRESHOLDS = [
    0.0,
    3.0,
    4.0,
    5.0,
    6.0,
    7.0,
    8.0,
    9.0,
    10.0,
    12.0,
    15.0
]


class FilteredAgent(AgentEngine):

    def __init__(
        self,
        *args,
        min_ema_sma_distance=0.0,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.min_ema_sma_distance = (
            min_ema_sma_distance
        )

        self.filtered_signals = 0
        self.accepted_signals = 0

    def _open_signal_from_candle(
        self,
        signal,
        current_price,
        current_timestamp
    ):
        if signal not in ("BUY", "SELL"):
            return None

        analysis = self.strategy_engine.analyzer.analyze(
            self.data_manager.get_all()
        )

        sma_values = analysis.get("sma", [])
        ema_values = analysis.get("ema", [])

        if not sma_values or not ema_values:
            return None

        difference = abs(
            ema_values[-1] -
            sma_values[-1]
        )

        if difference < self.min_ema_sma_distance:
            self.filtered_signals += 1

            return {
                "status": "FILTERED",
                "signal": signal,
                "difference": difference
            }

        self.accepted_signals += 1

        return super()._open_signal_from_candle(
            signal=signal,
            current_price=current_price,
            current_timestamp=current_timestamp
        )


def load_candles(path):

    provider = DataProvider()

    return provider.load_candles(path)


def create_config():

    return AgentConfig(
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


def run_test(candles, threshold):

    config = create_config()

    agent = FilteredAgent(
        config=config,
        min_ema_sma_distance=threshold
    )

    agent.run(candles)

    closed_trades = (
        agent.trading_engine
        .trade_manager
        .trade_history
    )

    total_profit = sum(
        trade["profit"]
        for trade in closed_trades
    )

    wins = sum(
        1
        for trade in closed_trades
        if trade["profit"] > 0
    )

    losses = sum(
        1
        for trade in closed_trades
        if trade["profit"] < 0
    )

    gross_profit = sum(
        trade["profit"]
        for trade in closed_trades
        if trade["profit"] > 0
    )

    gross_loss = abs(
        sum(
            trade["profit"]
            for trade in closed_trades
            if trade["profit"] < 0
        )
    )

    if gross_loss > 0:
        profit_factor = (
            gross_profit /
            gross_loss
        )
    elif gross_profit > 0:
        profit_factor = float("inf")
    else:
        profit_factor = 0.0

    total_trades = len(closed_trades)

    win_rate = (
        wins / total_trades * 100.0
        if total_trades > 0
        else 0.0
    )

    balance = 1000.0
    peak = balance
    max_drawdown = 0.0

    for trade in closed_trades:

        balance += trade["profit"]

        if balance > peak:
            peak = balance

        drawdown = peak - balance

        if drawdown > max_drawdown:
            max_drawdown = drawdown

    return {
        "trades": total_trades,
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "profit": total_profit,
        "pf": profit_factor,
        "dd": max_drawdown,
        "filtered": agent.filtered_signals,
        "accepted": agent.accepted_signals
    }


def print_dataset(name, candles):

    print()
    print("=" * 120)
    print(name)
    print("=" * 120)

    print(
        f"{'FILTER':>10} "
        f"{'TRADES':>8} "
        f"{'WR':>8} "
        f"{'PROFIT':>12} "
        f"{'PF':>10} "
        f"{'DD':>12} "
        f"{'FILTERED':>10}"
    )

    print("-" * 120)

    results = []

    for threshold in DIFF_THRESHOLDS:

        result = run_test(
            candles,
            threshold
        )

        results.append(
            (threshold, result)
        )

        pf_text = (
            "inf"
            if result["pf"] == float("inf")
            else f"{result['pf']:.3f}"
        )

        print(
            f"{threshold:>9.1f} "
            f"{result['trades']:>8} "
            f"{result['win_rate']:>7.2f}% "
            f"{result['profit']:>12.4f} "
            f"{pf_text:>10} "
            f"{result['dd']:>12.4f} "
            f"{result['filtered']:>10}"
        )

    return results


def main():

    all_results = {}

    for name, path in DATASETS:

        candles = load_candles(path)

        all_results[name] = print_dataset(
            name,
            candles
        )

    print()
    print("=" * 120)
    print("CROSS-DATASET SUMMARY")
    print("=" * 120)

    print(
        f"{'FILTER':>10} "
        f"{'TRAIN PROFIT':>15} "
        f"{'TRAIN PF':>10} "
        f"{'VALID PROFIT':>15} "
        f"{'VALID PF':>10}"
    )

    print("-" * 120)

    train_results = dict(
        all_results["TRAIN"]
    )

    validation_results = dict(
        all_results["VALIDATION"]
    )

    for threshold in DIFF_THRESHOLDS:

        train = train_results[threshold]
        valid = validation_results[threshold]

        train_pf = (
            "inf"
            if train["pf"] == float("inf")
            else f"{train['pf']:.3f}"
        )

        valid_pf = (
            "inf"
            if valid["pf"] == float("inf")
            else f"{valid['pf']:.3f}"
        )

        print(
            f"{threshold:>9.1f} "
            f"{train['profit']:>15.4f} "
            f"{train_pf:>10} "
            f"{valid['profit']:>15.4f} "
            f"{valid_pf:>10}"
        )


if __name__ == "__main__":
    main()
