from src.agent.agent_engine import AgentEngine
from src.agent.agent_config import AgentConfig
from src.data.data_provider import DataProvider


DATASETS = [
    ("TRAIN", "data/backtest/BTCUSDT_1m_5000.json"),
    ("VALIDATION", "data/backtest/BTCUSDT_1m_validation_5000.json")
]


class NextCandleAgent(AgentEngine):

    def __init__(self, *args, mode="CURRENT", **kwargs):
        super().__init__(*args, **kwargs)
        self.mode = mode
        self.pending_signal = None
        self.pending_timestamp = None
        self.filtered_signals = 0

    def run_cycle(self, candles):

        if not candles:
            return None

        current = candles[-1]

        # Najpierw realizujemy sygnał potwierdzony
        # przez poprzednią świecę.
        if self.pending_signal is not None:

            signal = self.pending_signal
            timestamp = current.timestamp
            price = current.close

            self.pending_signal = None
            self.pending_timestamp = None

            return self._open_signal_from_candle(
                signal=signal,
                current_price=price,
                current_timestamp=timestamp
            )

        # Normalna analiza
        analysis = self.analyze(candles)
        signal = analysis["signal"]

        if signal not in ("BUY", "SELL"):
            return super().run_cycle(candles)

        previous = candles[-1]

        bullish = previous.close > previous.open
        bearish = previous.close < previous.open

        if signal == "BUY" and bullish:
            self.pending_signal = "BUY"
            self.pending_timestamp = previous.timestamp
            return {
                "status": "SIGNAL_CONFIRMED",
                "signal": "BUY"
            }

        if signal == "SELL" and bearish:
            self.pending_signal = "SELL"
            self.pending_timestamp = previous.timestamp
            return {
                "status": "SIGNAL_CONFIRMED",
                "signal": "SELL"
            }

        self.filtered_signals += 1

        return {
            "status": "FILTERED",
            "signal": signal
        }


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


def run_current(candles):

    agent = AgentEngine(
        config=create_config()
    )

    agent.run(candles)

    return get_stats(agent)


def run_confirmed(candles):

    agent = NextCandleAgent(
        config=create_config()
    )

    agent.run(candles)

    return get_stats(agent)


def get_stats(agent):

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

        dd = peak - balance

        if dd > max_dd:
            max_dd = dd

    return {
        "trades": total,
        "win_rate": win_rate,
        "profit": sum(profits),
        "pf": pf,
        "dd": max_dd
    }


def main():

    all_results = {}

    for name, path in DATASETS:

        provider = DataProvider()
        candles = provider.load_candles(path)

        current = run_current(candles)
        confirmed = run_confirmed(candles)

        all_results[name] = {
            "CURRENT": current,
            "NEXT": confirmed
        }

        print()
        print("=" * 110)
        print(name)
        print("=" * 110)

        print(
            f"{'MODE':>12} "
            f"{'TRADES':>8} "
            f"{'WR':>8} "
            f"{'PROFIT':>12} "
            f"{'PF':>10} "
            f"{'DD':>12}"
        )

        print("-" * 110)

        for mode, result in [
            ("CURRENT", current),
            ("NEXT", confirmed)
        ]:

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
                f"{result['dd']:>12.4f}"
            )

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

    for mode in ["CURRENT", "NEXT"]:

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
