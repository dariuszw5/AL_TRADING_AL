from src.agent.agent_config import AgentConfig
from src.agent.agent_engine import AgentEngine
from src.data.data_provider import DataProvider


DATA_FILE = "data/backtest/BTCUSDT_1m_5000.json"


def calculate_statistics(trades):
    total_trades = len(trades)

    winning_trades = sum(
        1 for trade in trades
        if trade["profit"] > 0
    )

    losing_trades = sum(
        1 for trade in trades
        if trade["profit"] < 0
    )

    win_rate = (
        winning_trades / total_trades * 100
        if total_trades > 0
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
        sum(trade["profit"] for trade in trades)
        / total_trades
        if total_trades > 0
        else 0.0
    )

    return {
        "trades": total_trades,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "expectancy": expectancy
    }


def run_backtest(max_position_candles):
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

    provider = DataProvider()

    candles = provider.load_candles(
        DATA_FILE
    )

    agent = AgentEngine(config)

    agent.run(candles)

    trades = (
        agent.trading_engine
        .trade_manager
        .trade_history
    )

    statistics = calculate_statistics(
        trades
    )

    total_profit = sum(
        trade["profit"]
        for trade in trades
    )

    return {
        "time": max_position_candles,
        "trades": statistics["trades"],
        "profit": total_profit,
        "balance": agent.balance,
        "win_rate": statistics["win_rate"],
        "profit_factor": statistics["profit_factor"],
        "drawdown": agent.get_max_drawdown(),
        "expectancy": statistics["expectancy"]
    }


def main():
    print("=== POSITION TIME MICRO OPTIMIZATION ===")
    print()

    results = []

    position_times = [
        200,
        205,
        210,
        215,
        220,
        225,
        230,
        235,
        240,
        245,
        250
    ]

    for position_time in position_times:
        result = run_backtest(position_time)
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
    print("=== RANKING ===")
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
