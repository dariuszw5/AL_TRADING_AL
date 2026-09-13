from src.agent.agent_engine import AgentEngine
from src.agent.agent_config import AgentConfig
from src.data.data_provider import DataProvider


DATASETS = [
    ("TRAIN", "data/backtest/BTCUSDT_1m_5000.json"),
    ("VALIDATION", "data/backtest/BTCUSDT_1m_validation_5000.json")
]

BUY_LEVELS = [
    29.60,
    29.55,
    29.50,
    29.45,
    29.40,
    29.35,
    29.30,
    29.25,
    29.20,
    29.15,
    29.10,
    29.05,
    29.00
]

DELAYS = [1, 2, 3, 4, 5]


class ThresholdAgent(AgentEngine):

    def __init__(self, *args, delay=1, **kwargs):
        super().__init__(*args, **kwargs)

        self.delay = delay
        self.pending_signal = None
        self.pending_count = 0

    def run_cycle(self, candles):

        if not candles:
            return None

        current = candles[-1]

        if self.pending_signal is not None:

            self.pending_count -= 1

            if self.pending_count <= 0:

                signal = self.pending_signal

                self.pending_signal = None
                self.pending_count = 0

                return self._open_signal_from_candle(
                    signal=signal,
                    current_price=current.close,
                    current_timestamp=current.timestamp
                )

            return {
                "status": "WAITING",
                "signal": self.pending_signal
            }

        analysis = self.strategy_engine.analyzer.analyze(candles)

        signal = self.decision_engine.decide(analysis)

        if signal not in ("BUY", "SELL"):
            return super().run_cycle(candles)

        candle = candles[-1]

        bullish = candle.close > candle.open
        bearish = candle.close < candle.open

        confirmed = (
            signal == "BUY" and bullish
        ) or (
            signal == "SELL" and bearish
        )

        if not confirmed:
            return {
                "status": "FILTERED",
                "signal": signal
            }

        self.pending_signal = signal
        self.pending_count = self.delay

        return {
            "status": "SIGNAL_CONFIRMED",
            "signal": signal,
            "delay": self.delay
        }


def create_config(buy_rsi):

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
        buy_rsi=buy_rsi,
        sell_rsi=70.0,
        min_difference=1.0,
        trading_fee=0.0,
        rsi_method="classic",
        max_position_candles=240
    )


def get_stats(agent):

    trades = agent.trading_engine.trade_manager.trade_history

    profits = [
        float(trade["profit"])
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

    total = len(profits)

    win_rate = (
        len(wins) / total * 100.0
        if total > 0
        else 0.0
    )

    return {
        "trades": total,
        "win_rate": win_rate,
        "profit": sum(profits),
        "pf": pf,
        "dd": max_dd
    }


def run_test(candles, buy_rsi, delay):

    agent = ThresholdAgent(
        config=create_config(buy_rsi),
        delay=delay
    )

    agent.run(candles)

    return get_stats(agent)


def print_result(buy_rsi, delay, result):

    pf_text = (
        "inf"
        if result["pf"] == float("inf")
        else f"{result['pf']:.3f}"
    )

    print(
        f"{buy_rsi:>8.2f} "
        f"{delay:>4} "
        f"{result['trades']:>8} "
        f"{result['win_rate']:>7.2f}% "
        f"{result['profit']:>12.4f} "
        f"{pf_text:>10} "
        f"{result['dd']:>12.4f}"
    )


def main():

    provider = DataProvider()

    for dataset_name, path in DATASETS:

        candles = provider.load_candles(path)

        print()
        print("#" * 100)
        print(f"# {dataset_name}")
        print("#" * 100)

        print()
        print("=" * 100)
        print("BUY RSI FINE SCAN | SELL FIXED = 70")
        print("=" * 100)

        print(
            f"{'BUY':>8} "
            f"{'D':>4} "
            f"{'TRADES':>8} "
            f"{'WR':>8} "
            f"{'PROFIT':>12} "
            f"{'PF':>10} "
            f"{'DD':>12}"
        )

        print("-" * 100)

        for buy_rsi in BUY_LEVELS:

            for delay in DELAYS:

                result = run_test(
                    candles,
                    buy_rsi=buy_rsi,
                    delay=delay
                )

                print_result(
                    buy_rsi,
                    delay,
                    result
                )


if __name__ == "__main__":
    main()
