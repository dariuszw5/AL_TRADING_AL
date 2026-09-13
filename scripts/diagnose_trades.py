from src.agent.agent_config import AgentConfig
from src.agent.agent_engine import AgentEngine
from src.data.data_provider import DataProvider


config = AgentConfig(
    symbol="BTCUSDT",
    interval="1m",
    limit=5000,
    initial_balance=1000.0,
    risk_percent=5.0,
    stop_loss_percent=2.5,
    max_exposure_percent=100.0,
    risk_reward_ratio=2.0,
    buy_rsi=30.0,
    sell_rsi=70.0,
    min_difference=1.0,
    trading_fee=0.0,
    rsi_method="classic",
    max_position_candles=240
)

provider = DataProvider()

candles = provider.load_candles(
    "data/backtest/BTCUSDT_1m_5000.json"
)

agent = AgentEngine(config)
agent.run(candles)

trades = agent.trading_engine.trade_manager.trade_history

print()
print("=== EXIT DIAGNOSTICS ===")
print()

for index, trade in enumerate(trades, start=1):

    entry_timestamp = trade["entry_timestamp"]
    exit_timestamp = trade["exit_timestamp"]

    duration_minutes = (
        exit_timestamp - entry_timestamp
    ) / 60000

    print(
        f"{index:>2}. "
        f"{trade['side']:>4} | "
        f"Entry={trade['entry_price']:>10.2f} | "
        f"Exit={trade['exit_price']:>10.2f} | "
        f"Duration={duration_minutes:>7.1f} min | "
        f"Profit={trade['profit']:>9.4f}"
    )

print()
print("Expected TIME_EXIT duration: 240 minutes")
print()
print(f"Trades:        {len(trades)}")
print(f"Final balance: {agent.balance:.4f}")
print(f"Max drawdown:  {agent.get_max_drawdown():.4f}")
