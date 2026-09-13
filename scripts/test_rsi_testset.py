from src.agent.agent_engine import AgentEngine
from src.agent.agent_config import AgentConfig
from src.data.data_provider import DataProvider


TEST_FILE = "data/backtest/BTCUSDT_1m_test_5000.json"

BUY_LEVELS = [
    29.55,
    29.50,
    29.45,
    29.40,
    29.35,
    29.30,
    29.25
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

        analysis = self.strategy_engine.analyzer.analyze(
            candles
        )

        signal = self.decision_engine.decide(
            analysis
        )

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

    wins = [
        p for p in profits
        if p > 0
    ]

    losses = [
        p for p in profits
        if p < 0
    ]

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

    expectancy = (
        sum(profits) / total
        if total > 0
        else 0.0
    )

    return {
        "trades": total,
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": win_rate,
        "profit": sum(profits),
        "pf": pf,
        "dd": max_dd,
        "expectancy": expectancy,
        "final": balance
    }


def run_test(candles, buy_rsi, delay):

    agent = ThresholdAgent(
        config=create_config(buy_rsi),
        delay=delay
    )

    agent.run(candles)

    return get_stats(agent)


def main():

    provider = DataProvider()

    candles = provider.load_candles(TEST_FILE)

    print()
    print("=" * 140)
    print("TEST | BUY RSI FINE SCAN")
    print("=" * 140)
    print(f"Dataset: {TEST_FILE}")
    print("SELL RSI: 70.00")
    print("RSI: classic")
    print("Candles:", len(candles))
    print("=" * 140)

    print(
        f"{'BUY':>8} "
        f"{'D':>4} "
        f"{'TRADES':>8} "
        f"{'WINS':>6} "
        f"{'LOSS':>6} "
        f"{'WR':>8} "
        f"{'PROFIT':>12} "
        f"{'PF':>10} "
        f"{'DD':>12} "
        f"{'EXP':>10} "
        f"{'FINAL':>12}"
    )

    print("-" * 140)

    for buy_rsi in BUY_LEVELS:

        for delay in DELAYS:

            result = run_test(
                candles,
                buy_rsi=buy_rsi,
                delay=delay
            )

            pf_text = (
                "inf"
                if result["pf"] == float("inf")
                else f"{result['pf']:.3f}"
            )

            print(
                f"{buy_rsi:>8.2f} "
                f"{delay:>4} "
                f"{result['trades']:>8} "
                f"{result['wins']:>6} "
                f"{result['losses']:>6} "
                f"{result['win_rate']:>7.2f}% "
                f"{result['profit']:>12.4f} "
                f"{pf_text:>10} "
                f"{result['dd']:>12.4f} "
                f"{result['expectancy']:>10.4f} "
                f"{result['final']:>12.4f}"
            )

    print()
    print("=" * 140)
    print("TEST COMPLETE")
    print("=" * 140)


if __name__ == "__main__":
    main()
