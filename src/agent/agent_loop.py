from time import sleep

from src.agent.agent_engine import AgentEngine
from src.agent.agent_config import AgentConfig
from src.data.data_provider import DataProvider


class AgentLoop:
    def __init__(self, config=None):
        self.config = config or AgentConfig()
        self.agent = AgentEngine()
        self.data_provider = DataProvider()

    def run_once(self, candles=None):
        if candles is None:
            candles = self.data_provider.get_candles(
                symbol=self.config.symbol,
                interval=self.config.interval,
                limit=self.config.limit
            )

        return self.agent.run_cycle(candles)

    def run(self, candles=None, iterations=1, interval=60):
        results = []

        for _ in range(iterations):
            result = self.run_once(candles)
            results.append(result)

            if interval > 0:
                sleep(interval)

        return results