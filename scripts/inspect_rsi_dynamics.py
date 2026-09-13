from src.agent.agent_engine import AgentEngine
from src.agent.agent_config import AgentConfig
from src.data.data_provider import DataProvider
from src.analysis.indicators import rsi


DATASETS = [
    ("TRAIN", "data/backtest/BTCUSDT_1m_5000.json"),
    ("VALIDATION", "data/backtest/BTCUSDT_1m_validation_5000.json")
]

DELAYS = [1, 2, 3, 4, 5]


class RSIDynamicsAgent(AgentEngine):

    def __init__(self, *args, delay=1, **kwargs):
        super().__init__(*args, **kwargs)

        self.delay = delay
        self.pending_signal = None
        self.pending_count = 0
        self.signal_records = []

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

        candle_objects = []

        for candle in candles:
            if isinstance(candle, dict):
                candle = type(
                    "CandleObject",
                    (),
                    {
                        "timestamp": candle["timestamp"],
                        "open": float(candle["open"]),
                        "high": float(candle["high"]),
                        "low": float(candle["low"]),
                        "close": float(candle["close"]),
                        "volume": float(candle["volume"])
                    }
                )()

            candle_objects.append(candle)

        analysis = self.strategy_engine.analyzer.analyze(
            candle_objects
        )

        signal = self.decision_engine.decide(analysis)

        if signal not in ("BUY", "SELL"):
            return super().run_cycle(candles)

        candle = candle_objects[-1]

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

        closes = [
            float(c.close)
            for c in candle_objects
        ]

        rsi_values = rsi(closes, 14)

        if len(rsi_values) < 4:
            return {
                "status": "INSUFFICIENT_RSI",
                "signal": signal
            }

        r0 = rsi_values[-1]
        r1 = rsi_values[-2]
        r2 = rsi_values[-3]
        r3 = rsi_values[-4]

        self.signal_records.append({
            "signal": signal,
            "timestamp": candle.timestamp,
            "rsi_3": r3,
            "rsi_2": r2,
            "rsi_1": r1,
            "rsi_0": r0,
            "change_1": r0 - r1,
            "change_3": r0 - r3
        })

        self.pending_signal = signal
        self.pending_count = self.delay

        return {
            "status": "SIGNAL_CONFIRMED",
            "signal": signal,
            "delay": self.delay
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


def run_test(candles, delay):

    agent = RSIDynamicsAgent(
        config=create_config(),
        delay=delay
    )

    agent.run(candles)

    trades = agent.trading_engine.trade_manager.trade_history

    return agent, trades


def fmt(value):

    return f"{value:.2f}"


def print_results(dataset_name, delay, agent, trades):

    print()
    print("=" * 145)
    print(f"{dataset_name} | DELAY={delay}")
    print("=" * 145)

    print(
        f"{'#':>3} "
        f"{'SIDE':>6} "
        f"{'SIGNAL_TS':>16} "
        f"{'RSI-3':>8} "
        f"{'RSI-2':>8} "
        f"{'RSI-1':>8} "
        f"{'RSI':>8} "
        f"{'?1':>8} "
        f"{'?3':>8} "
        f"{'PROFIT':>12}"
    )

    print("-" * 145)

    used = set()

    for index, trade in enumerate(trades, start=1):

        entry_ts = trade.get("entry_timestamp")

        candidates = [
            (i, r)
            for i, r in enumerate(agent.signal_records)
            if i not in used
            and r["signal"] == trade["side"]
            and r["timestamp"] <= entry_ts
        ]

        if not candidates:
            continue

        signal_index, record = candidates[-1]
        used.add(signal_index)

        print(
            f"{index:>3} "
            f"{trade['side']:>6} "
            f"{str(record['timestamp']):>16} "
            f"{fmt(record['rsi_3']):>8} "
            f"{fmt(record['rsi_2']):>8} "
            f"{fmt(record['rsi_1']):>8} "
            f"{fmt(record['rsi_0']):>8} "
            f"{fmt(record['change_1']):>8} "
            f"{fmt(record['change_3']):>8} "
            f"{trade['profit']:>12.4f}"
        )


def main():

    provider = DataProvider()

    for dataset_name, path in DATASETS:

        candles = provider.load_candles(path)

        for delay in DELAYS:

            agent, trades = run_test(
                candles,
                delay
            )

            print_results(
                dataset_name,
                delay,
                agent,
                trades
            )


if __name__ == "__main__":
    main()
