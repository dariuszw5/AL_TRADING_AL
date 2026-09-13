from src.agent.agent_engine import AgentEngine
from src.agent.agent_config import AgentConfig
from src.data.data_provider import DataProvider


CONFIG = AgentConfig(
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
    max_position_candles=240,
)


class FilterAgent(AgentEngine):

    def __init__(
        self,
        config,
        buy_filter=0.0,
        sell_filter=0.0,
    ):
        super().__init__(config)

        self.buy_filter = buy_filter
        self.sell_filter = sell_filter
        self.filtered_signals = 0

    def _open_signal_from_candle(
        self,
        signal,
        current_price,
        current_timestamp,
    ):
        candles = self.data_manager.get_all()

        if len(candles) < 121:
            return None

        analysis = self.strategy_engine.analyzer.analyze(candles)

        sma_values = analysis.get("sma", [])
        ema_values = analysis.get("ema", [])

        if not sma_values or not ema_values:
            return None

        sma = float(sma_values[-1])
        ema = float(ema_values[-1])

        diff = abs(ema - sma)

        if signal == "BUY" and diff < self.buy_filter:
            self.filtered_signals += 1
            return None

        if signal == "SELL" and diff < self.sell_filter:
            self.filtered_signals += 1
            return None

        return super()._open_signal_from_candle(
            signal=signal,
            current_price=current_price,
            current_timestamp=current_timestamp,
        )


def load_candles(path):
    provider = DataProvider()
    return provider.load_candles(path)


def stats(trades):
    profits = [
        float(t["profit"])
        for t in trades
    ]

    if not profits:
        return 0, 0.0, 0.0, 0.0

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

    wr = len(wins) / len(profits) * 100.0

    return (
        len(profits),
        wr,
        sum(profits),
        pf,
    )


def run(path, buy_filter, sell_filter):

    candles = load_candles(path)

    agent = FilterAgent(
        CONFIG,
        buy_filter=buy_filter,
        sell_filter=sell_filter,
    )

    agent.run(candles)

    trades = (
        agent.trading_engine
        .trade_manager
        .trade_history
    )

    return stats(trades)


def main():

    train_path = (
        "data/backtest/"
        "BTCUSDT_1m_5000.json"
    )

    validation_path = (
        "data/backtest/"
        "BTCUSDT_1m_validation_5000.json"
    )

    buy_values = (
        0.0,
        8.0,
        10.0,
        12.0,
    )

    sell_values = (
        0.0,
        6.0,
        8.0,
        10.0,
        12.0,
    )

    print()
    print("=" * 105)
    print("EMA-SMA BUY / SELL COMBINATION TEST")
    print("=" * 105)

    print(
        f"{'BUY':>6} "
        f"{'SELL':>6} | "
        f"{'TRN N':>5} "
        f"{'TRN WR':>7} "
        f"{'TRN P':>10} "
        f"{'TRN PF':>7} | "
        f"{'VAL N':>5} "
        f"{'VAL WR':>7} "
        f"{'VAL P':>10} "
        f"{'VAL PF':>7}"
    )

    print("-" * 105)

    for buy_filter in buy_values:

        for sell_filter in sell_values:

            train = run(
                train_path,
                buy_filter,
                sell_filter,
            )

            validation = run(
                validation_path,
                buy_filter,
                sell_filter,
            )

            print(
                f"{buy_filter:6.1f} "
                f"{sell_filter:6.1f} | "
                f"{train[0]:5d} "
                f"{train[1]:6.2f}% "
                f"{train[2]:10.4f} "
                f"{train[3]:7.3f} | "
                f"{validation[0]:5d} "
                f"{validation[1]:6.2f}% "
                f"{validation[2]:10.4f} "
                f"{validation[3]:7.3f}"
            )


if __name__ == "__main__":
    main()
