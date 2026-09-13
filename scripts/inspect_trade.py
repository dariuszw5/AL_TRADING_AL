from src.agent.agent_engine import AgentEngine
from src.agent.agent_config import AgentConfig
from src.data.data_provider import DataProvider

config = AgentConfig(
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

provider = DataProvider()

candles = provider.load_candles(
    "data/backtest/BTCUSDT_1m_5000.json"
)

agent = AgentEngine(config)
agent.run(candles)

print()
print("NUMBER OF TRADES:", len(agent.trade_history.trades))
print()

if agent.trade_history.trades:
    print("FIRST TRADE:")
    print(agent.trade_history.trades[0])
    print()
    print("TYPE:")
    print(type(agent.trade_history.trades[0]))
    print()
    print("ATTRIBUTES:")
    print(dir(agent.trade_history.trades[0]))
