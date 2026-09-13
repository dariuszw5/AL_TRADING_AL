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


class ReversalAgent(AgentEngine):

    def __init__(self, config, mode):
        super().__init__(config)
        self.mode = mode

    def _closes(self, candles):
        return [candle.close for candle in candles]

    def _reversal(self, candles, lookback=120):
        closes = self._closes(candles)

        if len(closes) < lookback + 1:
            return "NONE"

        start = closes[-lookback - 1]
        previous = closes[-6]
        current = closes[-1]

        if start <= 0 or previous <= 0:
            return "NONE"

        long_change = ((current - start) / start) * 100.0
        short_change = ((current - previous) / previous) * 100.0

        if long_change <= -1.0 and short_change > 0:
            return "BUY_REVERSAL"

        if long_change >= 1.0 and short_change < 0:
            return "SELL_REVERSAL"

        return "NONE"

    def analyze(self, candles):
        result = super().analyze(candles)

        signal = result.get("signal", "HOLD")

        if signal == "BUY":
            if self.mode in (
                "BUY_REVERSAL_120",
                "COMBINED_REVERSAL_120",
            ):
                if self._reversal(candles, 120) != "BUY_REVERSAL":
                    result["signal"] = "HOLD"

        elif signal == "SELL":
            if self.mode in (
                "SELL_REVERSAL_120",
                "COMBINED_REVERSAL_120",
            ):
                if self._reversal(candles, 120) != "SELL_REVERSAL":
                    result["signal"] = "HOLD"

        return result


def load_candles(path):
    provider = DataProvider()
    return provider.load_candles(path)


def run_test(candles, mode):
    agent = ReversalAgent(CONFIG, mode)
    agent.run(candles)

    trades = len(agent.trade_history.trades)

    profit = agent.balance - CONFIG.initial_balance

    drawdown = agent.get_max_drawdown()

    return trades, profit, drawdown


def print_result(name, result):
    trades, profit, dd = result

    print(
        f"{name:<32} | "
        f"Trades={trades:3d} | "
        f"Profit={profit:10.4f} | "
        f"DD={dd:10.4f}"
    )


def main():
    provider = DataProvider()

    datasets = {
        "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
        "VALIDATION": "data/backtest/BTCUSDT_1m_validation_5000.json",
    }

    modes = [
        "CURRENT",
        "BUY_REVERSAL_120",
        "SELL_REVERSAL_120",
        "COMBINED_REVERSAL_120",
    ]

    for dataset_name, path in datasets.items():

        print()
        print("=" * 80)
        print(dataset_name)
        print("=" * 80)

        candles = provider.load_candles(path)

        for mode in modes:
            result = run_test(candles, mode)
            print_result(mode, result)


if __name__ == "__main__":
    main()
