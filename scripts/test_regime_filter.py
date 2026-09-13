from src.agent.agent_engine import AgentEngine
from src.agent.agent_config import AgentConfig
from src.data.data_provider import DataProvider


class RegimeFilteredAgent(AgentEngine):

    def __init__(self, config, mode):
        super().__init__(config)
        self.mode = mode

    def _regime(self, candles, lookback=120):
        if len(candles) <= lookback:
            return "FLAT"

        closes = []

        for candle in candles:
            if isinstance(candle, dict):
                closes.append(float(candle["close"]))
            else:
                closes.append(float(candle.close))

        start = closes[-lookback - 1]
        end = closes[-1]

        change = ((end - start) / start) * 100.0

        if change <= -1.0:
            return "STRONG_DOWN"
        if change < -0.2:
            return "DOWN"
        if change >= 1.0:
            return "STRONG_UP"
        if change > 0.2:
            return "UP"

        return "FLAT"

    def analyze(self, candles):
        result = super().analyze(candles)
        signal = result["signal"]

        regime = self._regime(candles, 120)

        if self.mode == "BUY_DOWN_STRONG_DOWN":
            if signal == "BUY" and regime not in ("DOWN", "STRONG_DOWN"):
                result["signal"] = "HOLD"

        elif self.mode == "SELL_DOWN":
            if signal == "SELL" and regime != "DOWN":
                result["signal"] = "HOLD"

        elif self.mode == "COMBINED":
            if signal == "BUY" and regime not in ("DOWN", "STRONG_DOWN"):
                result["signal"] = "HOLD"

            elif signal == "SELL" and regime != "DOWN":
                result["signal"] = "HOLD"

        return result


def run_test(candles, mode):
    config = AgentConfig(
        initial_balance=1000.0,
        buy_rsi=30.0,
        sell_rsi=70.0,
        min_difference=1.0,
        trading_fee=0.0,
        risk_percent=5.0,
        stop_loss_percent=5.0,
        risk_reward_ratio=2.0,
        max_exposure_percent=100.0,
        max_position_candles=240
    )

    if mode == "CURRENT":
        agent = AgentEngine(config)
    else:
        agent = RegimeFilteredAgent(config, mode)

    agent.run(candles)

    stats = agent.trading_engine.get_statistics()

    return {
        "trades": stats["total_trades"],
        "profit": stats["total_profit"],
        "drawdown": agent.get_max_drawdown()
    }


def main():
    provider = DataProvider()

    train = provider.load_candles(
        "data/backtest/BTCUSDT_1m_5000.json"
    )

    validation = provider.load_candles(
        "data/backtest/BTCUSDT_1m_validation_5000.json"
    )

    tests = [
        ("CURRENT", "CURRENT"),
        ("BUY_DOWN_STRONG_DOWN_120", "BUY_DOWN_STRONG_DOWN"),
        ("SELL_DOWN_120", "SELL_DOWN"),
        ("COMBINED_120", "COMBINED")
    ]

    for dataset_name, candles in [
        ("TRAIN", train),
        ("VALIDATION", validation)
    ]:

        print()
        print("=" * 75)
        print(dataset_name)
        print("=" * 75)

        for label, mode in tests:

            result = run_test(candles, mode)

            print(
                f"{label:35s} | "
                f"Trades={result['trades']:3d} | "
                f"Profit={result['profit']:10.4f} | "
                f"DD={result['drawdown']:10.4f}"
            )


if __name__ == "__main__":
    main()
