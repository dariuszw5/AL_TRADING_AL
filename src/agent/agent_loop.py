from time import sleep

from src.agent.agent_engine import AgentEngine
from src.agent.agent_config import AgentConfig
from src.data.data_provider import DataProvider
from src.agent.live_state_store import LiveStateStore


class AgentLoop:
    def __init__(self, config=None, state_file=None):
        self.config = config or AgentConfig()
        self.agent = AgentEngine(config=self.config)
        self.data_provider = DataProvider()

        self.history = []
        self.last_processed_timestamp = None

        self.state_store = (
            LiveStateStore(state_file)
            if state_file is not None
            else None
        )

        self._restore_state()

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

    def _serialize_state(self):
        position = self.agent.trading_engine.trade_manager.position

        return {
            "version": 3,
            "last_processed_timestamp": self.last_processed_timestamp,
            "position": position,
            "position_candles": self.agent.position_candles,
            "balance": self.agent.balance,
            "peak_balance": self.agent.peak_balance,
            "max_drawdown": self.agent.max_drawdown,
            "market_price": self.agent.market_price,
            "equity_curve": self.agent.equity_curve,

            # Agent-level trade history.
            "trade_history": list(
                self.agent.trade_history.get_trades()
            ),

            # TradingEngine/TradeManager closed-trade history.
            # This is the source used by get_statistics().
            "trade_manager_history": list(
                self.agent.trading_engine.trade_manager.trade_history
            ),

            "risk_guard": {
                "max_daily_loss": self.agent.risk_guard.max_daily_loss,
                "daily_loss": self.agent.risk_guard.daily_loss,
                "current_day": (
                    self.agent.risk_guard.current_day.isoformat()
                    if self.agent.risk_guard.current_day is not None
                    else None
                ),
            },
        }

    def _save_state(self):
        if self.state_store is not None:
            self.state_store.save(self._serialize_state())

    def _restore_state(self):
        if self.state_store is None:
            return

        state = self.state_store.load()

        if state is None:
            return

        self.last_processed_timestamp = state.get(
            "last_processed_timestamp"
        )

        position = state.get("position")

        self.agent.trading_engine.trade_manager.position = position

        self.agent.position_candles = state.get(
            "position_candles",
            0
        )

        if state.get("balance") is not None:
            self.agent.balance = state["balance"]

        if state.get("peak_balance") is not None:
            self.agent.peak_balance = state["peak_balance"]

        if state.get("max_drawdown") is not None:
            self.agent.max_drawdown = state["max_drawdown"]

        if state.get("market_price") is not None:
            self.agent.market_price = state["market_price"]

        if state.get("equity_curve") is not None:
            self.agent.equity_curve = state["equity_curve"]

        trade_history = state.get("trade_history")

        if trade_history is not None:
            self.agent.trade_history.trades = list(
                trade_history
            )

        trade_manager_history = state.get(
            "trade_manager_history"
        )

        if trade_manager_history is not None:
            self.agent.trading_engine.trade_manager.trade_history = list(
                trade_manager_history
            )

        risk_state = state.get("risk_guard")

        if risk_state is not None:

            if risk_state.get("max_daily_loss") is not None:
                self.agent.risk_guard.max_daily_loss = float(
                    risk_state["max_daily_loss"]
                )

            if risk_state.get("daily_loss") is not None:
                self.agent.risk_guard.daily_loss = float(
                    risk_state["daily_loss"]
                )

            current_day = risk_state.get("current_day")

            if current_day is not None:
                import datetime

                self.agent.risk_guard.current_day = (
                    datetime.date.fromisoformat(
                        current_day
                    )
                )
            else:
                self.agent.risk_guard.current_day = None

    def clear_state(self):
        if self.state_store is not None:
            self.state_store.clear()

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
                "position": (
                    self.agent.trading_engine.trade_manager.position
                ),
                "result": None,
                "error": str(exc),
            }

        if len(candles) < 2:
            return {
                "status": "WAITING_FOR_CANDLE",
                "signal": "HOLD",
                "position": (
                    self.agent.trading_engine.trade_manager.position
                ),
                "result": None
            }

        closed_candle = candles[-2]

        self._update_history(candles[:-1])

        if (
            self.last_processed_timestamp is not None
            and closed_candle.timestamp
            <= self.last_processed_timestamp
        ):
            return {
                "status": "NO_NEW_CANDLE",
                "timestamp": closed_candle.timestamp,
                "signal": "HOLD",
                "position": (
                    self.agent.trading_engine.trade_manager.position
                ),
                "result": None
            }

        previous_processed_timestamp = self.last_processed_timestamp

        result = self.agent.run_cycle(self.history)

        self.last_processed_timestamp = closed_candle.timestamp

        try:
            self._save_state()
        except Exception:
            # The candle is not considered processed unless persistence
            # succeeds. Preserve retryability after a failed save.
            self.last_processed_timestamp = previous_processed_timestamp
            raise

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
            results.append(
                self.run_live_once()
            )

            if interval > 0:
                sleep(interval)

        return results
