from src.agent.agent_config import AgentConfig
from src.agent.agent_engine import AgentEngine
from src.data.data_provider import DataProvider


DATA_FILE = "data/backtest/BTCUSDT_1m_validation_5000.json"


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

    win_rate = (
        wins / total * 100
        if total > 0
        else 0.0
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
        "balance": agent.balance,
        "win_rate": stats["win_rate"],
        "profit_factor": stats["profit_factor"],
        "drawdown": agent.get_max_drawdown(),
        "expectancy": stats["expectancy"]
    }


def main():
    print("=== POSITION TIME VALIDATION 240-540 ===")
    print()

    provider = DataProvider()

    candles = provider.load_candles(
        DATA_FILE
    )

    position_times = list(
        range(240, 541, 15)
    )

    results = []

    for time_value in position_times:

        result = run_backtest(
            time_value,
            candles
        )

        results.append(result)

        print(
            f"TIME={result['time']:>3} min | "
            f"Trades={result['trades']:>3} | "
            f"Profit={result['profit']:>10.4f} | "
            f"Balance={result['balance']:>10.4f} | "
            f"WR={result['win_rate']:>7.2f}% | "
            f"PF={result['profit_factor']:>7.4f} | "
            f"DD={result['drawdown']:>10.4f} | "
            f"Exp={result['expectancy']:>8.4f}"
        )

    print()
    print("=== VALIDATION RANKING ===")
    print()

    results.sort(
        key=lambda x: x["profit"],
        reverse=True
    )

    for index, result in enumerate(
        results,
        start=1
    ):
        print(
            f"{index:>2}. "
            f"TIME={result['time']:>3} min | "
            f"Profit={result['profit']:>10.4f} | "
            f"Balance={result['balance']:>10.4f} | "
            f"Trades={result['trades']:>3} | "
            f"WR={result['win_rate']:>7.2f}% | "
            f"PF={result['profit_factor']:>7.4f} | "
            f"DD={result['drawdown']:>10.4f} | "
            f"Exp={result['expectancy']:>8.4f}"
        )


if __name__ == "__main__":
    main()
