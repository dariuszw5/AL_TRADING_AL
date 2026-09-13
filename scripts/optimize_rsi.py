from src.agent.agent_config import AgentConfig
from src.agent.agent_engine import AgentEngine
from src.data.data_provider import DataProvider


DATA_FILE = "data/backtest/BTCUSDT_1m_5000.json"


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
        sum(
            trade["profit"]
            for trade in trades
        ) / total
        if total > 0
        else 0.0
    )

    return {
        "trades": total,
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "expectancy": expectancy
    }


def run_backtest(
    buy_rsi,
    sell_rsi,
    candles
):
    config = AgentConfig(
        symbol="BTCUSDT",
        interval="1m",
        limit=5000,
        initial_balance=1000.0,

        risk_percent=5.0,
        stop_loss_percent=5.0,
        max_exposure_percent=100.0,
        risk_reward_ratio=2.0,

        buy_rsi=buy_rsi,
        sell_rsi=sell_rsi,
        min_difference=1.0,

        trading_fee=0.0,
        rsi_method="classic",

        max_position_candles=240
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
        "buy_rsi": buy_rsi,
        "sell_rsi": sell_rsi,
        "trades": stats["trades"],
        "profit": profit,
        "balance": agent.balance,
        "win_rate": stats["win_rate"],
        "profit_factor": stats["profit_factor"],
        "drawdown": agent.get_max_drawdown(),
        "expectancy": stats["expectancy"]
    }


def main():
    print("=== RSI OPTIMIZATION ===")
    print()

    provider = DataProvider()

    candles = provider.load_candles(
        DATA_FILE
    )

    results = []

    for buy_rsi in range(25, 41):

        for sell_rsi in range(60, 76):

            if buy_rsi >= sell_rsi:
                continue

            result = run_backtest(
                buy_rsi=buy_rsi,
                sell_rsi=sell_rsi,
                candles=candles
            )

            results.append(result)

    results.sort(
        key=lambda x: (
            x["profit_factor"],
            x["expectancy"],
            x["profit"]
        ),
        reverse=True
    )

    print("=== TOP RSI RESULTS ===")
    print()

    for index, result in enumerate(
        results[:20],
        start=1
    ):
        print(
            f"{index:>2}. "
            f"BUY={result['buy_rsi']:>2} "
            f"SELL={result['sell_rsi']:>2} | "
            f"Trades={result['trades']:>3} | "
            f"Profit={result['profit']:>10.4f} | "
            f"Balance={result['balance']:>10.4f} | "
            f"WR={result['win_rate']:>7.2f}% | "
            f"PF={result['profit_factor']:>7.4f} | "
            f"DD={result['drawdown']:>10.4f} | "
            f"Exp={result['expectancy']:>8.4f}"
        )

    print()
    print("=== TOP RSI BY PROFIT ===")
    print()

    profit_results = sorted(
        results,
        key=lambda x: x["profit"],
        reverse=True
    )

    for index, result in enumerate(
        profit_results[:10],
        start=1
    ):
        print(
            f"{index:>2}. "
            f"BUY={result['buy_rsi']:>2} "
            f"SELL={result['sell_rsi']:>2} | "
            f"Profit={result['profit']:>10.4f} | "
            f"PF={result['profit_factor']:>7.4f} | "
            f"WR={result['win_rate']:>7.2f}% | "
            f"DD={result['drawdown']:>10.4f} | "
            f"Exp={result['expectancy']:>8.4f}"
        )


if __name__ == "__main__":
    main()
