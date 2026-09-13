from src.data.data_provider import DataProvider
from src.agent.agent_engine import AgentEngine
from src.agent.agent_config import AgentConfig


DATA_FILE = "data/backtest/BTCUSDT_1m_5000.json"


def main():
    provider = DataProvider()

    candles = provider.load_candles(DATA_FILE)

    config = AgentConfig(
        symbol="BTCUSDT",
        interval="1m",
        limit=5000,
        initial_balance=1000.0,
        risk_percent=5.0,
        risk_reward_ratio=2.0,
        buy_rsi=30.0,
        sell_rsi=70.0,
        min_difference=1.0,
        trading_fee=0.0,
        rsi_method="classic"
    )

    agent = AgentEngine(config=config)

    results = agent.run(candles)

    statistics = agent.trading_engine.get_statistics()

    trades = agent.trading_engine.trade_manager.trade_history

    profits = [
        float(trade["profit"])
        for trade in trades
    ]

    wins = [
        profit
        for profit in profits
        if profit > 0
    ]

    losses = [
        profit
        for profit in profits
        if profit < 0
    ]

    total_profit = sum(profits)

    if wins:
        average_win = sum(wins) / len(wins)
        largest_win = max(wins)
    else:
        average_win = 0.0
        largest_win = 0.0

    if losses:
        average_loss = sum(losses) / len(losses)
        largest_loss = min(losses)
    else:
        average_loss = 0.0
        largest_loss = 0.0

    gross_profit = sum(wins)

    gross_loss = abs(sum(losses))

    if gross_loss > 0:
        profit_factor = gross_profit / gross_loss
    else:
        profit_factor = float("inf")

    if profits:
        expectancy = total_profit / len(profits)
    else:
        expectancy = 0.0

    buy_signals = sum(
        1
        for result in results
        if result.get("signal") == "BUY"
    )

    sell_signals = sum(
        1
        for result in results
        if result.get("signal") == "SELL"
    )

    hold_signals = sum(
        1
        for result in results
        if result.get("signal") == "HOLD"
    )

    print()
    print("=" * 60)
    print("              AGENT BENCHMARK")
    print("=" * 60)

    print()
    print("=== DATA ===")
    print(f"Symbol:             {config.symbol}")
    print(f"Interval:           {config.interval}")
    print(f"Candles:            {len(candles)}")

    print()
    print("=== CONFIG ===")
    print(f"Initial balance:    {config.initial_balance}")
    print(f"Risk percent:       {config.risk_percent}")
    print(f"Risk/Reward:        {config.risk_reward_ratio}")
    print(f"Buy RSI:            {config.buy_rsi}")
    print(f"Sell RSI:           {config.sell_rsi}")
    print(f"Min difference:     {config.min_difference}")
    print(f"Trading fee:        {config.trading_fee}")
    print(f"RSI method:         {config.rsi_method}")

    print()
    print("=== SIGNALS ===")
    print(f"BUY:                {buy_signals}")
    print(f"SELL:               {sell_signals}")
    print(f"HOLD:               {hold_signals}")
    print(f"Total results:      {len(results)}")

    print()
    print("=== TRADING ===")
    print(f"Trades:             {statistics['total_trades']}")
    print(f"Winning trades:     {statistics['winning_trades']}")
    print(f"Losing trades:      {statistics['losing_trades']}")
    print(f"Win rate:           {statistics['win_rate']:.2f}%")

    print()
    print("=== PROFIT ===")
    print(f"Final balance:      {agent.balance:.4f}")
    print(f"Total profit:       {total_profit:.4f}")
    print(f"Average win:        {average_win:.4f}")
    print(f"Average loss:       {average_loss:.4f}")
    print(f"Largest win:        {largest_win:.4f}")
    print(f"Largest loss:       {largest_loss:.4f}")
    print(f"Profit factor:      {profit_factor:.4f}")
    print(f"Expectancy:         {expectancy:.4f}")

    print()
    print("=== RISK ===")
    print(f"Peak balance:       {agent.get_peak_balance():.4f}")
    print(f"Max drawdown:       {agent.get_max_drawdown():.4f}")

    print()
    print("=== FINAL POSITION ===")
    print(agent.trading_engine.trade_manager.position)

    print()
    print("=" * 60)
    print("                    END")
    print("=" * 60)


if __name__ == "__main__":
    main()
