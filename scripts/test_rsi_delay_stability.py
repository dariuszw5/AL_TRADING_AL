from statistics import median

from src.agent.agent_engine import AgentEngine
from src.agent.agent_config import AgentConfig
from src.data.data_provider import DataProvider


DATASETS = [
    ("TRAIN", "data/backtest/BTCUSDT_1m_5000.json"),
    ("VALIDATION", "data/backtest/BTCUSDT_1m_validation_5000.json")
]

RSI_CONFIGS = [
    ("30/70", 30.0, 70.0),
    ("32/68", 32.0, 68.0),
    ("35/65", 35.0, 65.0),
]

DELAYS = [1, 2, 3, 4, 5]


class ConfirmedEntryAgent(AgentEngine):

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

        analysis = self.analyze(candles)
        signal = analysis["signal"]

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


def create_config(buy_rsi, sell_rsi):

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
        sell_rsi=sell_rsi,
        min_difference=1.0,
        trading_fee=0.0,
        rsi_method="classic",
        max_position_candles=240
    )


def calculate_stats(agent):

    trades = agent.trading_engine.trade_manager.trade_history

    profits = [
        trade["profit"]
        for trade in trades
    ]

    total = len(profits)

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

    profit = sum(profits)

    if total > 0:
        wr = len(wins) / total * 100.0
        avg = profit / total
        med = median(profits)
    else:
        wr = 0.0
        avg = 0.0
        med = 0.0

    largest_win = max(profits) if profits else 0.0
    largest_loss = min(profits) if profits else 0.0

    if profit != 0:
        concentration = (
            abs(largest_win) / abs(profit)
        ) * 100.0
    else:
        concentration = 0.0

    balance = 1000.0
    peak = balance
    max_dd = 0.0

    for p in profits:

        balance += p

        if balance > peak:
            peak = balance

        dd = peak - balance

        if dd > max_dd:
            max_dd = dd

    return {
        "trades": total,
        "wr": wr,
        "profit": profit,
        "pf": pf,
        "dd": max_dd,
        "avg": avg,
        "median": med,
        "largest_win": largest_win,
        "largest_loss": largest_loss,
        "concentration": concentration
    }


def run_test(candles, buy_rsi, sell_rsi, delay):

    agent = ConfirmedEntryAgent(
        config=create_config(
            buy_rsi,
            sell_rsi
        ),
        delay=delay
    )

    agent.run(candles)

    return calculate_stats(agent)


def main():

    for dataset_name, path in DATASETS:

        provider = DataProvider()

        candles = provider.load_candles(path)

        print()
        print("=" * 150)
        print(dataset_name)
        print("=" * 150)

        print(
            f"{'RSI':>8} "
            f"{'D':>3} "
            f"{'TR':>4} "
            f"{'WR':>7} "
            f"{'PROFIT':>10} "
            f"{'PF':>8} "
            f"{'DD':>9} "
            f"{'AVG':>9} "
            f"{'MED':>9} "
            f"{'MAXW':>9} "
            f"{'MAXL':>9} "
            f"{'CONC':>8}"
        )

        print("-" * 150)

        for rsi_name, buy_rsi, sell_rsi in RSI_CONFIGS:

            for delay in DELAYS:

                result = run_test(
                    candles,
                    buy_rsi,
                    sell_rsi,
                    delay
                )

                pf_text = (
                    "inf"
                    if result["pf"] == float("inf")
                    else f"{result['pf']:.3f}"
                )

                print(
                    f"{rsi_name:>8} "
                    f"{delay:>3} "
                    f"{result['trades']:>4} "
                    f"{result['wr']:>6.2f}% "
                    f"{result['profit']:>10.4f} "
                    f"{pf_text:>8} "
                    f"{result['dd']:>9.4f} "
                    f"{result['avg']:>9.4f} "
                    f"{result['median']:>9.4f} "
                    f"{result['largest_win']:>9.4f} "
                    f"{result['largest_loss']:>9.4f} "
                    f"{result['concentration']:>7.2f}%"
                )


if __name__ == "__main__":
    main()
