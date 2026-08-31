from src.data.data_provider import DataProvider
from src.agent.agent_engine import AgentEngine
from src.agent.agent_config import AgentConfig

provider = DataProvider()

print("Pobieranie danych...")

candles = provider.get_historical_candles(
    symbol="BTCUSDT",
    interval="1m",
    limit=1000
)

agent = AgentEngine(
    config=AgentConfig(
        symbol="BTCUSDT",
        interval="1m",
        limit=1000,
        initial_balance=1000.0
    )
)

buy = 0
sell = 0
hold = 0

history = []

for candle in candles:
    history.append(candle)

    result = agent.analyze(history)
    signal = result["signal"]

    if signal == "BUY":
        buy += 1
    elif signal == "SELL":
        sell += 1
    else:
        hold += 1

print()
print("================================")
print("       ANALIZA SYGNALOW")
print("================================")
print(f"Swiece: {len(candles)}")
print(f"BUY:    {buy}")
print(f"SELL:   {sell}")
print(f"HOLD:   {hold}")
print("================================")
