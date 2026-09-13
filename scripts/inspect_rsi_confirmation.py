from src.agent.agent_engine import AgentEngine
from src.agent.agent_config import AgentConfig
from src.data.data_provider import DataProvider


DATASETS = [
    ("TRAIN", "data/backtest/BTCUSDT_1m_5000.json"),
    ("VALIDATION", "data/backtest/BTCUSDT_1m_validation_5000.json")
]

RSI_CONFIGS = [
    ("30/70", 30.0, 70.0),
    ("32/68", 32.0, 68.0)
]

DELAYS = [1, 2, 3]


class ConfirmedEntryAgent(AgentEngine):

    def __init__(self, *args, delay=1, **kwargs):
        super().__init__(*args, **kwargs)

        self.delay = delay
        self.pending_signal = None
        self.pending_count = 0
        self.filtered_signals = 0

        self.confirmed_signals = []

    def run_cycle(self, candles):

        if not candles:
            return None

        current = candles[-1]

        # -------------------------------------------------
        # OCZEKUJEMY NA WEJSCIE PO POTWIERDZONYM SYGNALE
        # -------------------------------------------------

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

                # Rejestrujemy TYLKO rzeczywiście otwartą pozycję.
                position = (
                    self.trading_engine
                    .trade_manager
                    .position
                )

                if position is not None:

                    self.confirmed_signals.append({
                        "signal": signal,
                        "signal_timestamp": signal_timestamp,
                        "signal_price": signal_price,
                        "entry_timestamp": position["entry_timestamp"],
                        "entry_price": position["entry_price"],
                        "side": position["side"],
                    })

                return result

            return {
                "status": "WAITING",
                "signal": self.pending_signal
            }

        # -------------------------------------------------
        # JEŻELI POZYCJA JEST OTWARTA
        # -------------------------------------------------

        if (
            self.trading_engine
            .trade_manager
            .position is not None
        ):
            return super().run_cycle(candles)

        # -------------------------------------------------
        # ANALIZA - IDENTYCZNA JAK W DZIALAJACYM TESCIE
        # -------------------------------------------------

        analysis = self.analyze(candles)
        signal = analysis["signal"]

        if signal not in ("BUY", "SELL"):
            return super().run_cycle(candles)

        # -------------------------------------------------
        # POTWIERDZENIE SWIECY
        # -------------------------------------------------

        bullish = current.close > current.open
        bearish = current.close < current.open

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

        # -------------------------------------------------
        # ZAPIS SYGNALU
        # -------------------------------------------------

        self.pending_signal = signal
        self.pending_count = self.delay

        self.pending_signal_timestamp = current.timestamp
        self.pending_signal_price = current.close

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


def run_test(candles, buy_rsi, sell_rsi, delay):

    agent = ConfirmedEntryAgent(
        config=create_config(
            buy_rsi,
            sell_rsi
        ),
        delay=delay
    )

    agent.run(candles)

    trades = (
        agent.trading_engine
        .trade_manager
        .trade_history
    )

    return agent, trades


def print_results(
    dataset_name,
    rsi_name,
    delay,
    agent,
    trades
):

    print()
    print(
        f"=== {dataset_name} | "
        f"RSI {rsi_name} | "
        f"DELAY={delay} ==="
    )

    print(
        f"Confirmed signals: {len(agent.confirmed_signals)}"
    )

    print(
        f"Closed trades:     {len(trades)}"
    )

    print(
        f"Filtered signals:  {agent.filtered_signals}"
    )

    print()

    count = min(
        len(agent.confirmed_signals),
        len(trades)
    )

    for i in range(count):

        signal = agent.confirmed_signals[i]
        trade = trades[i]

        delay_minutes = (
            trade["entry_timestamp"]
            - signal["signal_timestamp"]
        ) / 60000

        valid_pair = (
            trade["entry_timestamp"]
            == signal["entry_timestamp"]
        )

        marker = "OK" if valid_pair else "MISMATCH"

        print(
            f"{i + 1:>2}. "
            f"{signal['signal']:>4} | "
            f"SIGNAL={signal['signal_timestamp']} "
            f"px={signal['signal_price']:.2f} | "
            f"ENTRY={trade['entry_timestamp']} "
            f"px={trade['entry_price']:.2f} | "
            f"EXIT={trade['exit_timestamp']} "
            f"px={trade['exit_price']:.2f} | "
            f"DELAY={delay_minutes:.1f}m | "
            f"PROFIT={trade['profit']:.4f} | "
            f"{marker}"
        )

    print()

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
        if total > 0
        else 0.0
    )

    print(
        f"Trades={total} | "
        f"WR={win_rate:.2f}% | "
        f"Profit={sum(profits):.4f} | "
        f"PF={pf:.3f}"
    )


def main():

    for dataset_name, path in DATASETS:

        provider = DataProvider()
        candles = provider.load_candles(path)

        print()
        print("=" * 100)
        print(dataset_name)
        print("=" * 100)

        for rsi_name, buy_rsi, sell_rsi in RSI_CONFIGS:

            for delay in DELAYS:

                agent, trades = run_test(
                    candles,
                    buy_rsi,
                    sell_rsi,
                    delay
                )

                print_results(
                    dataset_name,
                    rsi_name,
                    delay,
                    agent,
                    trades
                )


if __name__ == "__main__":
    main()
