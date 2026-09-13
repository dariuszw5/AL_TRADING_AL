from src.agent.agent_engine import AgentEngine
from src.agent.agent_config import AgentConfig
from src.data.data_provider import DataProvider


BASE_CONFIG = AgentConfig(
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

        analysis = (
            self.strategy_engine
            .analyzer
            .analyze(candles)
        )

        sma_values = analysis.get("sma", [])
        ema_values = analysis.get("ema", [])

        if not sma_values or not ema_values:
            return None

        sma = float(sma_values[-1])
        ema = float(ema_values[-1])

        diff = abs(ema - sma)

        if signal == "BUY":
            if diff < self.buy_filter:
                self.filtered_signals += 1
                return None

        elif signal == "SELL":
            if diff < self.sell_filter:
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


def calculate_stats(trades):
    profits = [
        float(trade["profit"])
        for trade in trades
    ]

    if not profits:
        return {
            "trades": 0,
            "wr": 0.0,
            "profit": 0.0,
            "pf": 0.0,
        }

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

    return {
        "trades": len(profits),
        "wr": len(wins) / len(profits) * 100.0,
        "profit": sum(profits),
        "pf": pf,
    }


def run_test(
    path,
    buy_filter,
    sell_filter,
):
    candles = load_candles(path)

    agent = FilterAgent(
        BASE_CONFIG,
        buy_filter=buy_filter,
        sell_filter=sell_filter,
    )

    agent.run(candles)

    trades = (
        agent
        .trading_engine
        .trade_manager
        .trade_history
    )

    stats = calculate_stats(trades)

    stats["filtered"] = agent.filtered_signals

    return stats


def print_result(
    label,
    train,
    validation,
):
    print(
        f"{label:<24}"
        f"{train['trades']:>5} "
        f"{train['wr']:>7.2f}% "
        f"{train['profit']:>10.4f} "
        f"{train['pf']:>7.3f} "
        f"{train['filtered']:>7}   "
        f"{validation['trades']:>5} "
        f"{validation['wr']:>7.2f}% "
        f"{validation['profit']:>10.4f} "
        f"{validation['pf']:>7.3f} "
        f"{validation['filtered']:>7}"
    )


def main():

    train_path = (
        "data/backtest/"
        "BTCUSDT_1m_5000.json"
    )

    validation_path = (
        "data/backtest/"
        "BTCUSDT_1m_validation_5000.json"
    )

    filters = (
        0.0,
        4.0,
        6.0,
        8.0,
        10.0,
        12.0,
    )

    print()
    print("=" * 120)
    print("EMA-SMA SIDE FILTER TEST")
    print("=" * 120)

    print(
        f"{'CONFIG':<24}"
        f"{'TRN N':>5} "
        f"{'TRN WR':>8} "
        f"{'TRN P':>11} "
        f"{'TRN PF':>8} "
        f"{'TRN F':>8}   "
        f"{'VAL N':>5} "
        f"{'VAL WR':>8} "
        f"{'VAL P':>11} "
        f"{'VAL PF':>8} "
        f"{'VAL F':>8}"
    )

    print("-" * 120)

    print()
    print("BUY FILTER ONLY")
    print("-" * 120)

    for value in filters:

        train = run_test(
            train_path,
            buy_filter=value,
            sell_filter=0.0,
        )

        validation = run_test(
            validation_path,
            buy_filter=value,
            sell_filter=0.0,
        )

        print_result(
            f"BUY >= {value:.1f}",
            train,
            validation,
        )

    print()
    print("SELL FILTER ONLY")
    print("-" * 120)

    for value in filters:

        train = run_test(
            train_path,
            buy_filter=0.0,
            sell_filter=value,
        )

        validation = run_test(
            validation_path,
            buy_filter=0.0,
            sell_filter=value,
        )

        print_result(
            f"SELL >= {value:.1f}",
            train,
            validation,
        )

    print()
    print("SAME FILTER - BOTH SIDES")
    print("-" * 120)

    for value in filters:

        train = run_test(
            train_path,
            buy_filter=value,
            sell_filter=value,
        )

        validation = run_test(
            validation_path,
            buy_filter=value,
            sell_filter=value,
        )

        print_result(
            f"BOTH >= {value:.1f}",
            train,
            validation,
        )


if __name__ == "__main__":
    main()
