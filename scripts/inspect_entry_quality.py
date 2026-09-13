from src.agent.agent_engine import AgentEngine
from src.agent.agent_config import AgentConfig
from src.data.data_provider import DataProvider


DATASETS = [
    ("TRAIN", "data/backtest/BTCUSDT_1m_5000.json"),
    ("VALIDATION", "data/backtest/BTCUSDT_1m_validation_5000.json")
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


def fmt(value, digits=4):

    if value is None:
        return "None"

    if isinstance(value, float):
        return f"{value:.{digits}f}"

    return str(value)


def get_rsi(candles, agent):

    try:
        analysis = agent.analyze(candles)

        if "rsi" in analysis:
            return analysis["rsi"]

        if "indicators" in analysis:
            indicators = analysis["indicators"]

            if isinstance(indicators, dict):
                if "rsi" in indicators:
                    return indicators["rsi"]

    except Exception:
        pass

    return None


def candle_features(candle):

    body = candle.close - candle.open
    body_abs = abs(body)

    candle_range = candle.high - candle.low

    if candle_range > 0:
        body_ratio = body_abs / candle_range
    else:
        body_ratio = 0.0

    return {
        "body": body,
        "body_abs": body_abs,
        "range": candle_range,
        "body_ratio": body_ratio
    }


def inspect_dataset(dataset_name, path, delay):

    provider = DataProvider()
    candles = provider.load_candles(path)

    agent = ConfirmedEntryAgent(
        config=create_config(),
        delay=delay
    )

    agent.run(candles)

    trades = agent.trading_engine.trade_manager.trade_history

    print()
    print("=" * 170)
    print(
        f"{dataset_name} | RSI 30/70 | DELAY {delay}"
    )
    print("=" * 170)

    print(
        f"{'#':>3} "
        f"{'SIDE':>5} "
        f"{'ENTRY':>20} "
        f"{'EXIT':>20} "
        f"{'ENTRY P':>11} "
        f"{'EXIT P':>11} "
        f"{'PROFIT':>10} "
        f"{'SL':>11} "
        f"{'TP':>11} "
        f"{'QTY':>10}"
    )

    print("-" * 170)

    for i, trade in enumerate(trades, 1):

        print(
            f"{i:>3} "
            f"{trade['side']:>5} "
            f"{str(trade.get('entry_timestamp')):>20} "
            f"{str(trade.get('exit_timestamp')):>20} "
            f"{fmt(trade['entry_price']):>11} "
            f"{fmt(trade['exit_price']):>11} "
            f"{fmt(trade['profit']):>10} "
            f"{fmt(trade['stop_loss']):>11} "
            f"{fmt(trade['take_profit']):>11} "
            f"{fmt(trade['quantity'], 6):>10}"
        )

    print()
    print("TRADE QUALITY")
    print("-" * 170)

    for i, trade in enumerate(trades, 1):

        entry_ts = trade.get("entry_timestamp")

        entry_candle = None

        for candle in candles:
            if candle.timestamp == entry_ts:
                entry_candle = candle
                break

        if entry_candle is None:

            print(
                f"{i}: entry candle not found "
                f"| timestamp={entry_ts}"
            )

            continue

        features = candle_features(entry_candle)

        rsi = None

        try:
            index = candles.index(entry_candle)

            if index >= 99:
                rsi = get_rsi(
                    candles[:index + 1],
                    agent
                )

        except Exception:
            pass

        result = (
            "WIN"
            if trade["profit"] > 0
            else "LOSS"
            if trade["profit"] < 0
            else "BE"
        )

        print()
        print(
            f"TRADE #{i} | {result} | "
            f"{trade['side']} | "
            f"ENTRY={entry_ts}"
        )

        print(
            f"  OHLC: "
            f"O={fmt(entry_candle.open)} "
            f"H={fmt(entry_candle.high)} "
            f"L={fmt(entry_candle.low)} "
            f"C={fmt(entry_candle.close)}"
        )

        print(
            f"  Candle body:       {fmt(features['body'])}"
        )

        print(
            f"  Candle body abs:   {fmt(features['body_abs'])}"
        )

        print(
            f"  Candle range:      {fmt(features['range'])}"
        )

        print(
            f"  Body/range ratio:  "
            f"{features['body_ratio']:.4f}"
        )

        print(
            f"  RSI:               {fmt(rsi)}"
        )

        print(
            f"  Stop loss:         "
            f"{fmt(trade['stop_loss'])}"
        )

        print(
            f"  Take profit:       "
            f"{fmt(trade['take_profit'])}"
        )

        print(
            f"  Profit:            "
            f"{fmt(trade['profit'])}"
        )

        print("-" * 100)


def main():

    for dataset_name, path in DATASETS:

        for delay in DELAYS:

            inspect_dataset(
                dataset_name,
                path,
                delay
            )


if __name__ == "__main__":
    main()
