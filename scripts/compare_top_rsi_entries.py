from src.agent.agent_engine import AgentEngine
from src.agent.agent_config import AgentConfig
from src.data.data_provider import DataProvider


DATASETS = [
    ("TRAIN", "data/backtest/BTCUSDT_1m_5000.json"),
    ("VALIDATION", "data/backtest/BTCUSDT_1m_validation_5000.json")
]

CONFIGS = [
    ("30/70+3", 30.0, 70.0, 3),
    ("32/68+3", 32.0, 68.0, 3),
    ("35/65+2", 35.0, 65.0, 2),
]


class ConfirmedEntryAgent(AgentEngine):

    def __init__(self, *args, delay=1, **kwargs):
        super().__init__(*args, **kwargs)

        self.delay = delay
        self.pending_signal = None
        self.pending_count = 0
        self.pending_signal_timestamp = None
        self.pending_signal_price = None

        self.entries = []
        self.filtered_signals = 0

    def run_cycle(self, candles):

        if not candles:
            return None

        current = candles[-1]

        if self.pending_signal is not None:

            self.pending_count -= 1

            if self.pending_count <= 0:

                signal = self.pending_signal

                signal_timestamp = self.pending_signal_timestamp
                signal_price = self.pending_signal_price

                self.pending_signal = None
                self.pending_count = 0
                self.pending_signal_timestamp = None
                self.pending_signal_price = None

                result = self._open_signal_from_candle(
                    signal=signal,
                    current_price=current.close,
                    current_timestamp=current.timestamp
                )

                position = self.trading_engine.trade_manager.position

                if position is not None:

                    self.entries.append({
                        "signal": signal,
                        "signal_timestamp": signal_timestamp,
                        "signal_price": signal_price,
                        "entry_timestamp": current.timestamp,
                        "entry_price": current.close,
                        "side": position["side"]
                    })

                return result

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

            self.filtered_signals += 1

            return {
                "status": "FILTERED",
                "signal": signal
            }

        self.pending_signal = signal
        self.pending_count = self.delay

        self.pending_signal_timestamp = candle.timestamp
        self.pending_signal_price = candle.close

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


def ts(timestamp):

    from datetime import datetime, timezone

    return datetime.fromtimestamp(
        timestamp / 1000,
        tz=timezone.utc
    ).strftime("%Y-%m-%d %H:%M")


def run_config(candles, name, buy_rsi, sell_rsi, delay):

    agent = ConfirmedEntryAgent(
        config=create_config(buy_rsi, sell_rsi),
        delay=delay
    )

    agent.run(candles)

    trades = agent.trading_engine.trade_manager.trade_history

    records = []

    for entry in agent.entries:

        matching_trade = None

        for trade in trades:

            if (
                trade["entry_timestamp"]
                == entry["entry_timestamp"]
            ):
                matching_trade = trade
                break

        if matching_trade is None:
            continue

        records.append({
            "config": name,
            "signal": entry["signal"],
            "signal_timestamp": entry["signal_timestamp"],
            "signal_price": entry["signal_price"],
            "entry_timestamp": entry["entry_timestamp"],
            "entry_price": entry["entry_price"],
            "exit_timestamp": matching_trade["exit_timestamp"],
            "exit_price": matching_trade["exit_price"],
            "profit": matching_trade["profit"]
        })

    return records


def compare(dataset_name, candles):

    all_records = {}

    for name, buy_rsi, sell_rsi, delay in CONFIGS:

        all_records[name] = run_config(
            candles,
            name,
            buy_rsi,
            sell_rsi,
            delay
        )

    print()
    print("=" * 150)
    print(f"DATASET: {dataset_name}")
    print("=" * 150)

    for name in all_records:

        print()
        print(f"--- {name} ---")

        for index, record in enumerate(
            all_records[name],
            start=1
        ):

            print(
                f"{index:>2}. "
                f"{record['signal']:>4} "
                f"SIGNAL={ts(record['signal_timestamp'])} "
                f"ENTRY={ts(record['entry_timestamp'])} "
                f"EXIT={ts(record['exit_timestamp'])} "
                f"PROFIT={record['profit']:>9.4f}"
            )

    print()
    print("=" * 150)
    print("PAIRWISE OVERLAP")
    print("=" * 150)

    names = list(all_records.keys())

    for i in range(len(names)):

        for j in range(i + 1, len(names)):

            first = all_records[names[i]]
            second = all_records[names[j]]

            first_times = {
                r["signal_timestamp"]
                for r in first
            }

            second_times = {
                r["signal_timestamp"]
                for r in second
            }

            common = sorted(
                first_times & second_times
            )

            only_first = sorted(
                first_times - second_times
            )

            only_second = sorted(
                second_times - first_times
            )

            print()
            print(
                f"{names[i]}  VS  {names[j]}"
            )

            print(
                f"Wspolne wejscia: {len(common)}"
            )

            for timestamp in common:

                first_record = next(
                    r for r in first
                    if r["signal_timestamp"] == timestamp
                )

                second_record = next(
                    r for r in second
                    if r["signal_timestamp"] == timestamp
                )

                print(
                    f"  COMMON {ts(timestamp)} "
                    f"{first_record['signal']:>4} "
                    f"P1={first_record['profit']:>9.4f} "
                    f"P2={second_record['profit']:>9.4f}"
                )

            print(
                f"Tylko {names[i]}: {len(only_first)}"
            )

            for timestamp in only_first:

                record = next(
                    r for r in first
                    if r["signal_timestamp"] == timestamp
                )

                print(
                    f"  ONLY {ts(timestamp)} "
                    f"{record['signal']:>4} "
                    f"P={record['profit']:>9.4f}"
                )

            print(
                f"Tylko {names[j]}: {len(only_second)}"
            )

            for timestamp in only_second:

                record = next(
                    r for r in second
                    if r["signal_timestamp"] == timestamp
                )

                print(
                    f"  ONLY {ts(timestamp)} "
                    f"{record['signal']:>4} "
                    f"P={record['profit']:>9.4f}"
                )


def main():

    for dataset_name, path in DATASETS:

        provider = DataProvider()

        candles = provider.load_candles(path)

        compare(
            dataset_name,
            candles
        )


if __name__ == "__main__":
    main()
