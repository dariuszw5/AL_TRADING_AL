from time import sleep

from src.agent.agent_engine import AgentEngine
from src.agent.agent_config import AgentConfig
from src.data.data_provider import DataProvider


class AgentLoop:
    def __init__(self, config=None):
        self.config = config or AgentConfig()
        self.agent = AgentEngine(config=self.config)
        self.data_provider = DataProvider()

        self.history = []
        self.last_processed_timestamp = None

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

    def _update_history(self, candles):
        for candle in candles:
            if not self.history or candle.timestamp > self.history[-1].timestamp:
                self.history.append(candle)

        if len(self.history) > self.config.limit:
            self.history = self.history[-self.config.limit:]

        return self.history

    def run_live_once(self):
        try:
            candles = self.data_provider.get_candles(
                symbol=self.config.symbol,
                interval=self.config.interval,
                limit=self.config.limit
            )
        except Exception as exc:
            return {
                "status": "API_ERROR",
                "signal": "HOLD",
                "position": self.agent.trading_engine.trade_manager.position,
                "result": None,
                "error": str(exc),
            }

        if len(candles) < 2:
            return {
                "status": "WAITING_FOR_CANDLE",
                "signal": "HOLD",
                "position": self.agent.trading_engine.trade_manager.position,
                "result": None
            }

        closed_candle = candles[-2]

        self._update_history(candles[:-1])

        if (
            self.last_processed_timestamp is not None
            and closed_candle.timestamp <= self.last_processed_timestamp
        ):
            return {
                "status": "NO_NEW_CANDLE",
                "timestamp": closed_candle.timestamp,
                "signal": "HOLD",
                "position": self.agent.trading_engine.trade_manager.position,
                "result": None
            }

        self.last_processed_timestamp = closed_candle.timestamp

        result = self.agent.run_cycle(self.history)

        return {
            "status": "PROCESSED",
            "timestamp": closed_candle.timestamp,
            "signal": result.get("signal"),
            "position": result.get("position"),
            "result": result.get("result")
        }

    def run_live(self, iterations=1, interval=60):
        results = []

        for _ in range(iterations):
            results.append(self.run_live_once())

            if interval > 0:
                sleep(interval)

        return results
