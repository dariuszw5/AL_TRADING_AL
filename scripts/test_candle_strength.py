from src.agent.agent_engine import AgentEngine
from src.agent.agent_config import AgentConfig
from src.data.data_provider import DataProvider


DATASETS = [
    ("TRAIN", "data/backtest/BTCUSDT_1m_5000.json"),
    ("VALIDATION", "data/backtest/BTCUSDT_1m_validation_5000.json")
]

BODY_THRESHOLDS = [0.0, 0.25, 0.50, 0.75]


class CandleStrengthAgent(AgentEngine):

    def __init__(
        self,
        *args,
        min_body_ratio=0.0,
        use_confirmation=False,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.min_body_ratio = min_body_ratio
        self.use_confirmation = use_confirmation
        self.filtered_signals = 0

    def _open_signal_from_candle(
        self,
        signal,
        current_price,
        current_timestamp
    ):

        if signal not in ("BUY", "SELL"):
            return None

        if not self.use_confirmation:
            return super()._open_signal_from_candle(
                signal=signal,
                current_price=current_price,
                current_timestamp=current_timestamp
            )

        candles = self.data_manager.get_all()

        if not candles:
            return None

        candle = candles[-1]

        candle_range = candle.high - candle.low
        body = abs(candle.close - candle.open)

        if candle_range <= 0:
            self.filtered_signals += 1
            return {
                "status": "FILTERED",
                "signal": signal
            }

        body_ratio = body / candle_range

        if signal == "BUY":
            direction_ok = candle.close > candle.open
        else:
            direction_ok = candle.close < candle.open

        strength_ok = body_ratio >= self.min_body_ratio

        if not direction_ok or not strength_ok:

            self.filtered_signals += 1

            return {
                "status": "FILTERED",
                "signal": signal,
                "body_ratio": body_ratio
            }

        return super()._open_signal_from_candle(
            signal=signal,
            current_price=current_price,
            current_timestamp=current_timestamp
        )


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


def run_test(candles, threshold, use_confirmation):

    agent = CandleStrengthAgent(
        config=create_config(),
        min_body_ratio=threshold,
        use_confirmation=use_confirmation
    )

    agent.run(candles)

    trades = (
        agent.trading_engine
        .trade_manager
        .trade_history
    )

    profits = [
        trade["profit"]
        for trade in trades
    ]

    wins = [p for p in profits if p > 0]
    losses = [p for p in profits if p < 0]

    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))

    if gross_loss > 0:
        pf = gross_profit / gross_loss
    elif gross_profit > 0:
        pf = float("inf")
    else:
        pf = 0.0

    total = len(profits)

    win_rate = (
        len(wins) / total * 100.0
        if total > 0
        else 0.0
    )

    balance = 1000.0
    peak = balance
    max_dd = 0.0

    for profit in profits:

        balance += profit

        if balance > peak:
            peak = balance

        drawdown = peak - balance

        if drawdown > max_dd:
            max_dd = drawdown

    return {
        "trades": total,
        "win_rate": win_rate,
        "profit": sum(profits),
        "pf": pf,
        "dd": max_dd,
        "filtered": agent.filtered_signals
    }


def main():

    all_results = {}

    for dataset_name, path in DATASETS:

        provider = DataProvider()
        candles = provider.load_candles(path)

        print()
        print("=" * 115)
        print(dataset_name)
        print("=" * 115)

        print(
            f"{'MODE':>12} "
            f"{'TRADES':>8} "
            f"{'WR':>8} "
            f"{'PROFIT':>12} "
            f"{'PF':>10} "
            f"{'DD':>12} "
            f"{'FILTERED':>10}"
        )

        print("-" * 115)

        results = {}

        baseline = run_test(
            candles,
            0.0,
            False
        )

        results["CURRENT"] = baseline

        print(
            f"{'CURRENT':>12} "
            f"{baseline['trades']:>8} "
            f"{baseline['win_rate']:>7.2f}% "
            f"{baseline['profit']:>12.4f} "
            f"{baseline['pf']:>10.3f} "
            f"{baseline['dd']:>12.4f} "
            f"{baseline['filtered']:>10}"
        )

        for threshold in BODY_THRESHOLDS:

            if threshold == 0.0:
                name = "1 CANDLE"
            else:
                name = f"BODY {threshold:.0%}"

            result = run_test(
                candles,
                threshold,
                True
            )

            results[name] = result

            pf_text = (
                "inf"
                if result["pf"] == float("inf")
                else f"{result['pf']:.3f}"
            )

            print(
                f"{name:>12} "
                f"{result['trades']:>8} "
                f"{result['win_rate']:>7.2f}% "
                f"{result['profit']:>12.4f} "
                f"{pf_text:>10} "
                f"{result['dd']:>12.4f} "
                f"{result['filtered']:>10}"
            )

        all_results[dataset_name] = results

    print()
    print("=" * 115)
    print("CROSS-DATASET SUMMARY")
    print("=" * 115)

    print(
        f"{'MODE':>12} "
        f"{'TRAIN P':>12} "
        f"{'TRAIN PF':>10} "
        f"{'VALID P':>12} "
        f"{'VALID PF':>10}"
    )

    print("-" * 115)

    names = [
        "CURRENT",
        "1 CANDLE",
        "BODY 25%",
        "BODY 50%",
        "BODY 75%"
    ]

    for name in names:

        train = all_results["TRAIN"][name]
        valid = all_results["VALIDATION"][name]

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
            f"{name:>12} "
            f"{train['profit']:>12.4f} "
            f"{train_pf:>10} "
            f"{valid['profit']:>12.4f} "
            f"{valid_pf:>10}"
        )


if __name__ == "__main__":
    main()
