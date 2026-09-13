from src.agent.agent_engine import AgentEngine
from src.agent.agent_config import AgentConfig


agent = AgentEngine(config=AgentConfig())

print("RISK_GUARD TYPE:")
print(type(agent.risk_guard))
print()

print("RISK_GUARD __dict__:")
print(agent.risk_guard.__dict__)
print()

print("TRADE_HISTORY TYPE:")
print(type(agent.trade_history))
print()

print("TRADE_HISTORY __dict__:")
print(agent.trade_history.__dict__)
print()

print("AGENT ENGINE RELEVANT STATE:")
for name, value in agent.__dict__.items():
    print(f"{name} = {value!r}")
