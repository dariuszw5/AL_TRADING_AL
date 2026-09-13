from src.agent.agent_engine import AgentEngine
from src.agent.agent_config import AgentConfig
from src.data.data_provider import DataProvider


DATASETS = [
    ("TRAIN", "data/backtest/BTCUSDT_1m_5000.json"),
    ("VALIDATION", "data/backtest/BTCUSDT_1m_validation_5000.json")
]


class CandleConfirmationAgent(AgentEngine):

    def __init__(self, *args, confirmation_candles=1, **kwargs):
        super().__init__(*args, **kwargs)
        self.confirmation_candles = confirmation_candles
        self.filtered_signals = 0

    def _open_signal_from_candle(
        self,
        signal,
        current_price,
        current_timestamp
    ):
        candles = self.data_manager.get_all()

        required = self.confirmation_candles

        if len(candles) < required:
            return None

        recent = candles[-required:]

        bullish = all(
            candle.close > candle.open
            for candle in recent
        )

        bearish = all(
            candle.close < candle.open
            for candle in recent
        )

        allowed = (
            signal == "BUY" and bullish
        ) or (
            signal == "SELL" and bearish
        )

        if not allowed:
            self.filtered_signals += 1

            return {
                "status": "FILTERED",
                "signal": signal
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


def run_test(candles, confirmation_candles):
    agent = CandleConfirmationAgent(
        config=create_config(),
        confirmation_candles=confirmation_candles
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
        len(wins) / total * 100
        if total
        else 0.0
    )

    balance = 1000.0
    peak = balance
    max_dd = 0.0

    for profit in profits:
        balance += profit

        if balance > peak:
            peak = balance

        dd = peak - balance

        if dd > max_dd:
            max_dd = dd

    return {
        "trades": total,
        "win_rate": win_rate,
        "profit": sum(profits),
        "pf": pf,
        "dd": max_dd,
        "filtered": agent.filtered_signals
    }


def main():

    modes = [
        ("CURRENT", 0),
        ("1 CANDLE", 1),
        ("2 CANDLES", 2)
    ]

    all_results = {}

    for dataset_name, path in DATASETS:

        provider = DataProvider()
        candles = provider.load_candles(path)

        print()
        print("=" * 110)
        print(dataset_name)
        print("=" * 110)

        print(
            f"{'MODE':>12} "
            f"{'TRADES':>8} "
            f"{'WR':>8} "
            f"{'PROFIT':>12} "
            f"{'PF':>10} "
            f"{'DD':>12} "
            f"{'FILTERED':>10}"
        )

        print("-" * 110)

        dataset_results = {}

        for name, count in modes:

            if count == 0:

                result = run_test(
                    candles,
                    0
                )

            else:

                result = run_test(
                    candles,
                    count
                )

            dataset_results[name] = result

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

        all_results[dataset_name] = dataset_results

    print()
    print("=" * 110)
    print("CROSS-DATASET SUMMARY")
    print("=" * 110)

    print(
        f"{'MODE':>12} "
        f"{'TRAIN P':>12} "
        f"{'TRAIN PF':>10} "
        f"{'VALID P':>12} "
        f"{'VALID PF':>10}"
    )

    print("-" * 110)

    for name, _ in modes:

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
