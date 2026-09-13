from src.agent.agent_engine import AgentEngine
from src.agent.agent_config import AgentConfig
from src.data.data_provider import DataProvider


DATASETS = [
    ("TRAIN", "data/backtest/BTCUSDT_1m_5000.json"),
    ("VALIDATION", "data/backtest/BTCUSDT_1m_validation_5000.json"),
    ("TEST", "data/backtest/BTCUSDT_1m_test_5000.json"),
]

BUY_LEVELS = [
    33.00,
    33.25,
    33.50,
    33.75,
    34.00,
    34.25,
    34.50,
    34.75,
    35.00,
    35.25,
    35.50,
    35.75,
    36.00,
    36.25,
    36.50,
    36.75,
    37.00,
]

SELL_RSI = 70.0
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
        sell_rsi=SELL_RSI,
        min_difference=1.0,
        trading_fee=0.0,
        rsi_method="classic",
        max_position_candles=240,
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
        "final": balance,
    }


def run_test(candles, buy_rsi, delay):

    agent = ThresholdAgent(
        config=create_config(buy_rsi),
        delay=delay,
    )

    agent.run(candles)

    return get_stats(agent)


def pf_text(value):

    if value == float("inf"):
        return "inf"

    return f"{value:.3f}"


def main():

    provider = DataProvider()

    all_results = {}

    print()
    print("=" * 165)
    print("BUY RSI FINE SCAN | CROSS DATASET")
    print("=" * 165)
    print("BUY RSI: 33.00 - 37.00 | STEP: 0.25")
    print("SELL RSI: 70.00")
    print("RSI: classic")
    print("DELAYS: 1-5")
    print("=" * 165)

    for dataset_name, path in DATASETS:

        candles = provider.load_candles(path)

        all_results[dataset_name] = {}

        print()
        print("#" * 165)
        print(f"# {dataset_name}")
        print(f"# Dataset: {path}")
        print(f"# Candles: {len(candles)}")
        print("#" * 165)

        print(
            f"{'BUY':>8} "
            f"{'D':>4} "
            f"{'TRADES':>8} "
            f"{'WR':>8} "
            f"{'PROFIT':>12} "
            f"{'PF':>10} "
            f"{'DD':>12} "
            f"{'EXP':>10} "
            f"{'FINAL':>12}"
        )

        print("-" * 165)

        for buy_rsi in BUY_LEVELS:

            all_results[dataset_name][buy_rsi] = {}

            for delay in DELAYS:

                result = run_test(
                    candles,
                    buy_rsi,
                    delay,
                )

                all_results[dataset_name][buy_rsi][delay] = result

                print(
                    f"{buy_rsi:>8.2f} "
                    f"{delay:>4} "
                    f"{result['trades']:>8} "
                    f"{result['win_rate']:>7.2f}% "
                    f"{result['profit']:>12.4f} "
                    f"{pf_text(result['pf']):>10} "
                    f"{result['dd']:>12.4f} "
                    f"{result['expectancy']:>10.4f} "
                    f"{result['final']:>12.4f}"
                )

            print()

    print()
    print("=" * 165)
    print("CROSS-DATASET SUMMARY | AVERAGE OVER DELAYS")
    print("=" * 165)

    print(
        f"{'BUY':>8} "
        f"{'TRAIN':>12} "
        f"{'VALID':>12} "
        f"{'TEST':>12} "
        f"{'AVG':>12} "
        f"{'WORST':>12} "
        f"{'POS':>8}"
    )

    print("-" * 165)

    summary = {}

    for buy_rsi in BUY_LEVELS:

        values = {}

        for dataset_name, _ in DATASETS:

            profits = [
                all_results[dataset_name][buy_rsi][delay]["profit"]
                for delay in DELAYS
            ]

            values[dataset_name] = sum(profits) / len(profits)

        average = sum(values.values()) / len(values)
        worst = min(values.values())

        positive = sum(
            1
            for value in values.values()
            if value > 0
        )

        summary[buy_rsi] = {
            "train": values["TRAIN"],
            "validation": values["VALIDATION"],
            "test": values["TEST"],
            "average": average,
            "worst": worst,
            "positive": positive,
        }

        print(
            f"{buy_rsi:>8.2f} "
            f"{values['TRAIN']:>12.4f} "
            f"{values['VALIDATION']:>12.4f} "
            f"{values['TEST']:>12.4f} "
            f"{average:>12.4f} "
            f"{worst:>12.4f} "
            f"{positive:>7}/3"
        )

    ranked = sorted(
        summary.items(),
        key=lambda item: (
            item[1]["positive"],
            item[1]["worst"],
            item[1]["average"],
        ),
        reverse=True,
    )

    print()
    print("=" * 165)
    print("ROBUSTNESS RANKING")
    print("=" * 165)

    print(
        f"{'RANK':>6} "
        f"{'BUY':>8} "
        f"{'TRAIN':>12} "
        f"{'VALID':>12} "
        f"{'TEST':>12} "
        f"{'AVG':>12} "
        f"{'WORST':>12} "
        f"{'POS':>8}"
    )

    print("-" * 165)

    for rank, (buy_rsi, data) in enumerate(ranked, start=1):

        print(
            f"{rank:>6} "
            f"{buy_rsi:>8.2f} "
            f"{data['train']:>12.4f} "
            f"{data['validation']:>12.4f} "
            f"{data['test']:>12.4f} "
            f"{data['average']:>12.4f} "
            f"{data['worst']:>12.4f} "
            f"{data['positive']:>7}/3"
        )

    print()
    print("=" * 165)
    print("FINE SCAN COMPLETE")
    print("=" * 165)


if __name__ == "__main__":
    main()
