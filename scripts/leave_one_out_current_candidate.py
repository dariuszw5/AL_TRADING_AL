from pathlib import Path

from src.data.data_provider import DataProvider
from src.agent.agent_config import AgentConfig
from src.agent.agent_engine import AgentEngine


BUY = 33.8
SELL = 68.5
TIME = 241
FEE = 0.0004

DATASETS = [
    ("OOS #1", "data/backtest/BTCUSDT_1m_forward_5000.json"),
    ("OOS #2", "data/backtest/BTCUSDT_1m_forward_5000_oos2.json"),
]


def get_trades(path):
    provider = DataProvider()
    candles = provider.load_candles(Path(path))

    config = AgentConfig(
        buy_rsi=BUY,
        sell_rsi=SELL,
        max_position_candles=TIME,
        trading_fee=FEE,
        rsi_method="classic",
    )

    engine = AgentEngine(config=config)
    engine.run(candles)

    return engine.trading_engine.trade_manager.trade_history


def print_dataset(name, trades):
    profits = [float(t["profit"]) for t in trades]
    total = sum(profits)

    print()
    print("=" * 100)
    print(f"{name} | LEAVE-ONE-OUT | CURRENT FROZEN CANDIDATE")
    print("=" * 100)
    print(f"Trades : {len(profits)}")
    print(f"Profit : {total:.4f}")
    print("-" * 100)

    ranked = sorted(
        enumerate(profits, 1),
        key=lambda x: x[1],
        reverse=True,
    )

    print("REMOVE # | REMOVED PROFIT | REMAINING PROFIT")
    print("-" * 100)

    for index, profit in ranked:
        remaining = total - profit
        print(
            f"{index:8d} | "
            f"{profit:15.4f} | "
            f"{remaining:16.4f}"
        )


def main():
    all_trades = []

    for name, path in DATASETS:
        trades = get_trades(path)
        print_dataset(name, trades)
        all_trades.extend(trades)

    profits = [float(t["profit"]) for t in all_trades]
    total = sum(profits)

    print()
    print("=" * 100)
    print("OOS #1 + OOS #2 | COMBINED LEAVE-ONE-OUT")
    print("=" * 100)
    print(f"Trades : {len(profits)}")
    print(f"Profit : {total:.4f}")
    print("-" * 100)
    print("RANK | REMOVED PROFIT | REMAINING PROFIT")
    print("-" * 100)

    ranked = sorted(
        enumerate(profits, 1),
        key=lambda x: x[1],
        reverse=True,
    )

    for rank, (index, profit) in enumerate(ranked[:10], 1):
        remaining = total - profit
        print(
            f"{rank:4d} | "
            f"{profit:15.4f} | "
            f"{remaining:16.4f}"
        )

    top3 = sum(profit for _, profit in ranked[:3])
    top5 = sum(profit for _, profit in ranked[:5])

    print()
    print("=" * 100)
    print("CONCENTRATION SUMMARY")
    print("=" * 100)
    print(f"Top 1 removed : {total - ranked[0][1]:.4f}")
    print(f"Top 3 removed : {total - top3:.4f}")
    print(f"Top 5 removed : {total - top5:.4f}")
    print("=" * 100)


if __name__ == "__main__":
    main()
