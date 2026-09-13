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


def run_dataset(name, path):
    print("=" * 118)
    print(f"=== {name} | SELL SIGNAL STRENGTH ===")
    print("=" * 118)
    print(
        f"BUY={BUY} | SELL={SELL} | TIME={TIME} | "
        f"RSI=classic | FEE={FEE}"
    )
    print()

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

    trades = engine.trading_engine.trade_manager.trade_history

    sell_trades = [
        trade for trade in trades
        if str(trade.get("side", "")).upper() == "SELL"
    ]

    print(f"SELL TRADES: {len(sell_trades)}")
    print("-" * 118)

    if not sell_trades:
        print("Brak transakcji SELL.")
        print()
        return

    for i, trade in enumerate(sell_trades, 1):
        profit = trade.get("profit")
        entry_price = trade.get("entry_price")
        exit_price = trade.get("exit_price")
        entry_timestamp = trade.get("entry_timestamp")
        exit_timestamp = trade.get("exit_timestamp")
        exit_reason = trade.get("exit_reason", "N/A")

        print(
            f"{i:2d}. "
            f"PROFIT={profit if profit is not None else 'N/A':>10} | "
            f"ENTRY={entry_price if entry_price is not None else 'N/A':>10} | "
            f"EXIT={exit_price if exit_price is not None else 'N/A':>10} | "
            f"ENTRY_TS={entry_timestamp if entry_timestamp is not None else 'N/A'} | "
            f"EXIT_TS={exit_timestamp if exit_timestamp is not None else 'N/A'} | "
            f"EXIT_REASON={exit_reason}"
        )

    print()
    print("RSI zostanie odtworzone osobno z historii świec dla każdego")
    print("wejścia SELL, ponieważ transakcje nie przechowują wartości RSI.")
    print()


if __name__ == "__main__":
    for dataset_name, dataset_path in DATASETS:
        run_dataset(dataset_name, dataset_path)

    print("=" * 118)
    print("=== END ===")
    print("=" * 118)
