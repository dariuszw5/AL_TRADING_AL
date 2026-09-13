from src.agent.agent_engine import AgentEngine
from src.agent.agent_config import AgentConfig
from src.data.data_provider import DataProvider


DATASETS = [
    ("TRAIN", "data/backtest/BTCUSDT_1m_5000.json"),
    ("VALIDATION", "data/backtest/BTCUSDT_1m_validation_5000.json")
]

CONFIGS = [
    ("30/70", 30.0, 70.0, 3),
    ("32/68", 32.0, 68.0, 3),
    ("35/65", 35.0, 65.0, 2),
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

        # ---------------------------------------------------------
        # PENDING SIGNAL
        # ---------------------------------------------------------

        if self.pending_signal is not None:

            self.pending_count -= 1

            if self.pending_count <= 0:

                signal = self.pending_signal

                signal_timestamp = self.pending_signal_timestamp
                signal_price = self.pending_signal_price

                self.pending_signal = None
                self.pending_count = 0

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
                        "side": position["side"],
                    })

                return result

            return {
                "status": "WAITING",
                "signal": self.pending_signal
            }

        # ---------------------------------------------------------
        # NORMAL CYCLE
        # ---------------------------------------------------------

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


def format_timestamp(timestamp):

    from datetime import datetime, timezone

    return datetime.fromtimestamp(
        timestamp / 1000,
        tz=timezone.utc
    ).strftime("%Y-%m-%d %H:%M:%S")


def run_config(candles, name, buy_rsi, sell_rsi, delay):

    agent = ConfirmedEntryAgent(
        config=create_config(buy_rsi, sell_rsi),
        delay=delay
    )

    agent.run(candles)

    trades = agent.trading_engine.trade_manager.trade_history

    print()
    print("=" * 120)
    print(f"CONFIG: RSI {name} | DELAY {delay}")
    print("=" * 120)

    print(
        f"{'#':>3} "
        f"{'SIDE':>5} "
        f"{'SIGNAL TIME':>20} "
        f"{'ENTRY TIME':>20} "
        f"{'EXIT TIME':>20} "
        f"{'ENTRY':>12} "
        f"{'EXIT':>12} "
        f"{'PROFIT':>12}"
    )

    print("-" * 120)

    for index, trade in enumerate(trades, start=1):

        entry = None

        for candidate in agent.entries:

            if candidate["entry_timestamp"] == trade["entry_timestamp"]:
                entry = candidate
                break

        if entry is None:
            continue

        print(
            f"{index:>3} "
            f"{trade['side']:>5} "
            f"{format_timestamp(entry['signal_timestamp']):>20} "
            f"{format_timestamp(trade['entry_timestamp']):>20} "
            f"{format_timestamp(trade['exit_timestamp']):>20} "
            f"{trade['entry_price']:>12.2f} "
            f"{trade['exit_price']:>12.2f} "
            f"{trade['profit']:>12.4f}"
        )

    print()
    print(f"Filtered signals: {agent.filtered_signals}")
    print(f"Closed trades:    {len(trades)}")

    total_profit = sum(
        trade["profit"]
        for trade in trades
    )

    print(f"Total profit:     {total_profit:.4f}")


def main():

    for dataset_name, path in DATASETS:

        provider = DataProvider()
        candles = provider.load_candles(path)

        print()
        print("#" * 120)
        print(f"DATASET: {dataset_name}")
        print("#" * 120)

        for name, buy_rsi, sell_rsi, delay in CONFIGS:

            run_config(
                candles,
                name,
                buy_rsi,
                sell_rsi,
                delay
            )


if __name__ == "__main__":
    main()
