from src.agent.agent_config import AgentConfig
from src.agent.agent_engine import AgentEngine
from src.data.data_provider import DataProvider


TRAIN_FILE = "data/backtest/BTCUSDT_1m_5000.json"
VALIDATION_FILE = "data/backtest/BTCUSDT_1m_validation_5000.json"


def calculate_statistics(trades):
    total = len(trades)

    wins = sum(
        1
        for trade in trades
        if trade["profit"] > 0
    )

    losses = sum(
        1
        for trade in trades
        if trade["profit"] < 0
    )

    gross_profit = sum(
        trade["profit"]
        for trade in trades
        if trade["profit"] > 0
    )

    gross_loss = sum(
        abs(trade["profit"])
        for trade in trades
        if trade["profit"] < 0
    )

    if gross_loss > 0:
        profit_factor = gross_profit / gross_loss
    elif gross_profit > 0:
        profit_factor = float("inf")
    else:
        profit_factor = 0.0

    win_rate = (
        wins / total * 100
        if total > 0
        else 0.0
    )

    expectancy = (
        sum(trade["profit"] for trade in trades) / total
        if total > 0
        else 0.0
    )

    return {
        "trades": total,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "expectancy": expectancy
    }


def run_backtest(max_position_candles, candles):
    config = AgentConfig(
        symbol="BTCUSDT",
        interval="1m",
        limit=5000,
        initial_balance=1000.0,

        risk_percent=5.0,
        stop_loss_percent=5.0,
        max_exposure_percent=100.0,
        risk_reward_ratio=2.0,

        buy_rsi=30.0,
        sell_rsi=70.0,
        min_difference=1.0,

        trading_fee=0.0,
        rsi_method="classic",

        max_position_candles=max_position_candles
    )

    agent = AgentEngine(config)

    agent.run(candles)

    trades = (
        agent.trading_engine
        .trade_manager
        .trade_history
    )

    stats = calculate_statistics(trades)

    profit = sum(
        trade["profit"]
        for trade in trades
    )

    return {
        "time": max_position_candles,
        "trades": stats["trades"],
        "profit": profit,
        "win_rate": stats["win_rate"],
        "profit_factor": stats["profit_factor"],
        "drawdown": agent.get_max_drawdown(),
        "expectancy": stats["expectancy"]
    }


def main():
    print("=== TRAIN vs VALIDATION POSITION TIME ===")
    print()

    provider = DataProvider()

    train_candles = provider.load_candles(
        TRAIN_FILE
    )

    validation_candles = provider.load_candles(
        VALIDATION_FILE
    )

    position_times = [
        405,
        420,
        435,
        450,
        465,
        480,
        495,
        510,
        525,
        540
    ]

    results = []

    for time_value in position_times:

        train = run_backtest(
            time_value,
            train_candles
        )

        validation = run_backtest(
            time_value,
            validation_candles
        )

        train_profit = train["profit"]
        validation_profit = validation["profit"]

        if train_profit != 0:
            generalization = (
                validation_profit / train_profit
            )
        else:
            generalization = 0.0

        result = {
            "time": time_value,
            "train": train,
            "validation": validation,
            "generalization": generalization
        }

        results.append(result)

        print(
            f"TIME={time_value:>3} min | "
            f"TRAIN={train_profit:>9.4f} | "
            f"VALID={validation_profit:>9.4f} | "
            f"TRAIN PF={train['profit_factor']:>6.3f} | "
            f"VALID PF={validation['profit_factor']:>6.3f} | "
            f"TRAIN WR={train['win_rate']:>6.2f}% | "
            f"VALID WR={validation['win_rate']:>6.2f}% | "
            f"VALID DD={validation['drawdown']:>8.4f} | "
            f"VALID EXP={validation['expectancy']:>7.4f}"
        )

    print()
    print("=== GENERALIZATION RANKING ===")
    print()

    results.sort(
        key=lambda x: x["validation"]["profit"],
        reverse=True
    )

    for index, result in enumerate(
        results,
        start=1
    ):
        train = result["train"]
        validation = result["validation"]

        print(
            f"{index:>2}. "
            f"TIME={result['time']:>3} min | "
            f"TRAIN={train['profit']:>9.4f} | "
            f"VALID={validation['profit']:>9.4f} | "
            f"VALID PF={validation['profit_factor']:>6.3f} | "
            f"VALID DD={validation['drawdown']:>8.4f} | "
            f"VALID EXP={validation['expectancy']:>7.4f}"
        )


if __name__ == "__main__":
    main()
