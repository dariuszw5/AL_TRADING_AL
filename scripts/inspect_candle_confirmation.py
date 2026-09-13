from src.agent.agent_engine import AgentEngine
from src.agent.agent_config import AgentConfig
from src.data.data_provider import DataProvider


DATASETS = [
    (
        "TRAIN",
        "data/backtest/BTCUSDT_1m_5000.json"
    ),
    (
        "VALIDATION",
        "data/backtest/BTCUSDT_1m_validation_5000.json"
    )
]


class CandleConfirmationAgent(AgentEngine):

    def _open_signal_from_candle(
        self,
        signal,
        current_price,
        current_timestamp
    ):

        candles = self.data_manager.get_all()

        if not candles:
            return None

        candle = candles[-1]

        if signal == "BUY" and candle.close <= candle.open:
            return {
                "status": "FILTERED",
                "signal": signal
            }

        if signal == "SELL" and candle.close >= candle.open:
            return {
                "status": "FILTERED",
                "signal": signal
            }

        return super()._open_signal_from_candle(
            signal=signal,
            current_price=current_price,
            current_timestamp=current_timestamp
        )


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


def main():

    provider = DataProvider()

    for name, path in DATASETS:

        candles = provider.load_candles(path)

        agent = CandleConfirmationAgent(
            config=create_config()
        )

        agent.run(candles)

        trades = (
            agent.trading_engine
            .trade_manager
            .trade_history
        )

        print()
        print("=" * 130)
        print(name)
        print("=" * 130)

        print(
            f"{'#':>3} "
            f"{'SIDE':>6} "
            f"{'ENTRY':>12} "
            f"{'EXIT':>12} "
            f"{'PROFIT':>10} "
            f"{'SL':>12} "
            f"{'TP':>12}"
        )

        print("-" * 130)

        for i, trade in enumerate(trades, 1):

            print(
                f"{i:>3} "
                f"{trade['side']:>6} "
                f"{trade['entry_price']:>12.2f} "
                f"{trade['exit_price']:>12.2f} "
                f"{trade['profit']:>10.4f} "
                f"{trade['stop_loss']:>12.2f} "
                f"{trade['take_profit']:>12.2f}"
            )

        print()
        print("LICZBA TRANSAKCJI:", len(trades))

        if trades:

            profits = [
                trade["profit"]
                for trade in trades
            ]

            print(
                "SUMA PROFIT:",
                round(sum(profits), 4)
            )

            print(
                "WIN RATE:",
                round(
                    sum(p > 0 for p in profits)
                    / len(profits)
                    * 100,
                    2
                ),
                "%"
            )


if __name__ == "__main__":
    main()
