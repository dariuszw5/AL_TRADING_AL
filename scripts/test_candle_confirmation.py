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


class CandleConfirmationAgent(AgentEngine):

    def __init__(
        self,
        *args,
        mode="BOTH",
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.mode = mode
        self.filtered_signals = 0

    def _open_signal_from_candle(
        self,
        signal,
        current_price,
        current_timestamp
    ):

        if signal not in ("BUY", "SELL"):
            return None

        candles = self.data_manager.get_all()

        if not candles:
            return None

        candle = candles[-1]

        bullish = candle.close > candle.open
        bearish = candle.close < candle.open

        allowed = True

        if self.mode == "BUY":

            if signal == "BUY" and not bullish:
                allowed = False

        elif self.mode == "SELL":

            if signal == "SELL" and not bearish:
                allowed = False

        elif self.mode == "BOTH":

            if signal == "BUY" and not bullish:
                allowed = False

            if signal == "SELL" and not bearish:
                allowed = False

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


def load_candles(path):

    provider = DataProvider()

    return provider.load_candles(path)


def run_test(candles, mode):

    config = create_config()

    agent = CandleConfirmationAgent(
        config=config,
        mode=mode
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

    wins = [
        p for p in profits
        if p > 0
    ]

    losses = [
        p for p in profits
        if p < 0
    ]

    total_profit = sum(profits)

    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))

    if gross_loss > 0:

        pf = gross_profit / gross_loss

    elif gross_profit > 0:

        pf = float("inf")

    else:

        pf = 0.0

    total_trades = len(trades)

    win_rate = (
        len(wins) / total_trades * 100.0
        if total_trades > 0
        else 0.0
    )

    balance = 1000.0
    peak = balance
    max_drawdown = 0.0

    for trade in trades:

        balance += trade["profit"]

        if balance > peak:
            peak = balance

        drawdown = peak - balance

        if drawdown > max_drawdown:
            max_drawdown = drawdown

    return {
        "trades": total_trades,
        "win_rate": win_rate,
        "profit": total_profit,
        "pf": pf,
        "dd": max_drawdown,
        "filtered": agent.filtered_signals
    }


def main():

    modes = [
        "CURRENT",
        "BUY",
        "SELL",
        "BOTH"
    ]

    all_results = {}

    for dataset_name, path in DATASETS:

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

        candles = load_candles(path)

        dataset_results = {}

        for mode in modes:

            actual_mode = (
                "NONE"
                if mode == "CURRENT"
                else mode
            )

            result = run_test(
                candles,
                actual_mode
            )

            dataset_results[mode] = result

            pf_text = (
                "inf"
                if result["pf"] == float("inf")
                else f"{result['pf']:.3f}"
            )

            print(
                f"{mode:>12} "
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

    for mode in modes:

        train = all_results["TRAIN"][mode]
        valid = all_results["VALIDATION"][mode]

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
            f"{mode:>12} "
            f"{train['profit']:>12.4f} "
            f"{train_pf:>10} "
            f"{valid['profit']:>12.4f} "
            f"{valid_pf:>10}"
        )


if __name__ == "__main__":
    main()
