from src.data.data_provider import DataProvider
from src.data.data_manager import DataManager
from src.data.candle import Candle
from src.strategy.strategy_engine import StrategyEngine
from src.trading.trading_engine import TradingEngine
from src.agent.decision_engine import DecisionEngine
from src.agent.agent_config import AgentConfig
from src.agent.agent_state import AgentState
from src.agent.risk_guard import RiskGuard
from src.agent.trade_history import TradeHistory


class AgentEngine:

    def __init__(self, config=None):
        self.config = config or AgentConfig()
        self.agent_state = AgentState()

        self.balance = self.config.initial_balance
        self.peak_balance = self.balance
        self.max_drawdown = 0.0
        self.market_price = None
        self.equity_curve = [self.balance]

        self.trading_fee = float(
            self.config.trading_fee
        )

        self.data_provider = DataProvider()
        self.data_manager = DataManager()

        self.strategy_engine = StrategyEngine(
            initial_balance=self.config.initial_balance,
            buy_rsi=self.config.buy_rsi,
            sell_rsi=self.config.sell_rsi,
            min_difference=self.config.min_difference,
            rsi_method=self.config.rsi_method
        )

        self.trading_engine = TradingEngine()

        self.decision_engine = DecisionEngine(
            buy_rsi=self.config.buy_rsi,
            sell_rsi=self.config.sell_rsi,
            min_difference=self.config.min_difference,
            rsi_method=self.config.rsi_method
        )

        self.risk_guard = RiskGuard(
            max_daily_loss=self.config.initial_balance
            * (self.config.risk_percent / 100)
        )

        self.trading_engine.set_trade_result_callback(
            self._process_closed_trade
        )

        self.trade_history = TradeHistory()

    @property
    def state(self):
        return self.agent_state.get_state()

    @state.setter
    def state(self, value):
        self.agent_state.set_state(value)

    def analyze(self, candles):
        if self.agent_state.is_stopped():
            return {"signal": "HOLD"}

        self.agent_state.set_state("ANALYZING")

        candle_objects = []

        for candle in candles:
            if isinstance(candle, dict):
                candle = Candle(
                    timestamp=candle["timestamp"],
                    open=candle["open"],
                    high=candle["high"],
                    low=candle["low"],
                    close=candle["close"],
                    volume=candle["volume"]
                )

            self.data_manager.add_data(candle)
            candle_objects.append(candle)

        analysis = self.strategy_engine.analyzer.analyze(
            candle_objects
        )

        signal = self.decision_engine.decide(
            analysis
        )

        if not self.agent_state.is_stopped():
            self.agent_state.set_state("IDLE")

        return {"signal": signal}

    def execute_trade(
        self,
        signal,
        entry_price,
        quantity,
        stop_loss,
        take_profit,
        entry_timestamp=None
    ):
        if self.agent_state.is_stopped():
            return {
                "status": "REJECTED",
                "signal": signal
            }

        if not self.risk_guard.can_trade():
            return {
                "status": "RISK_BLOCKED",
                "signal": signal
            }

        if signal not in ("BUY", "SELL"):
            return {
                "status": "REJECTED",
                "signal": signal
            }

        if self.trading_engine.trade_manager.position is not None:
            return {
                "status": "ALREADY_OPEN",
                "signal": signal
            }

        self.agent_state.set_state("TRADING")

        result = self.trading_engine.process_signal(
            signal=signal,
            entry_price=entry_price,
            quantity=quantity,
            stop_loss=stop_loss,
            take_profit=take_profit,
            entry_timestamp=entry_timestamp
        )

        if result is None:
            self.agent_state.set_state("IDLE")

            return {
                "status": "REJECTED",
                "signal": signal
            }

        trade = {
            "signal": signal,
            "entry_price": entry_price,
            "quantity": quantity,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "entry_timestamp": entry_timestamp
        }

        self.trade_history.add_trade(trade)

        if self.market_price is None:
            self.market_price = entry_price

        if isinstance(result, dict):
            result["status"] = "OPEN"
            return result

        return {
            "status": "OPEN",
            "result": result,
            **trade
        }

    def _process_closed_trade(self, result):
        if result is None:
            return

        if not isinstance(result, dict):
            return

        gross_profit = result.get("profit")

        if gross_profit is None:
            return

        gross_profit = float(gross_profit)

        entry_price = float(
            result.get("entry_price", 0.0)
        )

        exit_price = float(
            result.get("exit_price", 0.0)
        )

        quantity = float(
            result.get("quantity", 0.0)
        )

        entry_notional = abs(
            entry_price * quantity
        )

        exit_notional = abs(
            exit_price * quantity
        )

        fee = (
            entry_notional + exit_notional
        ) * self.trading_fee

        net_profit = gross_profit - fee

        result["gross_profit"] = gross_profit
        result["fee"] = fee
        result["profit"] = net_profit

        self.balance += net_profit

        if self.balance > self.peak_balance:
            self.peak_balance = self.balance

        drawdown = self.peak_balance - self.balance

        if drawdown > self.max_drawdown:
            self.max_drawdown = drawdown

        self.equity_curve.append(self.balance)

        if net_profit < 0:
            self.risk_guard.record_loss(
                abs(net_profit)
            )

    def update_market_price(self, current_price):
        if current_price <= 0:
            raise ValueError(
                "Current price must be greater than 0"
            )

        self.market_price = float(current_price)

        equity = self.get_equity()

        if equity > self.peak_balance:
            self.peak_balance = equity

        drawdown = self.peak_balance - equity

        if drawdown > self.max_drawdown:
            self.max_drawdown = drawdown

        self.equity_curve.append(equity)

        return equity

    def get_equity(self):
        position = self.trading_engine.trade_manager.position

        if position is None:
            return self.balance

        current_price = (
            self.market_price
            if self.market_price is not None
            else position["entry_price"]
        )

        if position["side"] == "BUY":
            unrealized_profit = (
                current_price - position["entry_price"]
            ) * position["quantity"]
        else:
            unrealized_profit = (
                position["entry_price"] - current_price
            ) * position["quantity"]

        return self.balance + unrealized_profit

    def get_peak_balance(self):
        return self.peak_balance

    def get_drawdown(self):
        return max(
            0.0,
            self.peak_balance - self.get_equity()
        )

    def get_max_drawdown(self):
        return self.max_drawdown

    def get_equity_curve(self):
        return self.equity_curve.copy()

    def run_cycle(self, candles):
        if self.agent_state.is_stopped():
            return {
                "signal": "HOLD",
                "position": self.trading_engine.trade_manager.position,
                "result": None
            }

        analysis = self.analyze(candles)
        signal = analysis["signal"]

        position = self.trading_engine.trade_manager.position

        current_candle = candles[-1]

        if isinstance(current_candle, dict):
            current_price = current_candle["close"]
            current_timestamp = current_candle["timestamp"]
            current_high = current_candle["high"]
            current_low = current_candle["low"]
        else:
            current_price = current_candle.close
            current_timestamp = current_candle.timestamp
            current_high = current_candle.high
            current_low = current_candle.low

        self.update_market_price(current_price)

        if position is not None:
            self.agent_state.set_state("TRADING")

            result = self.trading_engine.check_candle(
                high=current_high,
                low=current_low,
                close=current_price,
                timestamp=current_timestamp
            )

            position = self.trading_engine.trade_manager.position

            if position is None:
                self.agent_state.set_state("IDLE")

            return {
                "signal": signal,
                "position": position,
                "result": result
            }

        if signal in ("BUY", "SELL"):
            if not self.risk_guard.can_trade():
                return {
                    "signal": signal,
                    "position": None,
                    "result": {
                        "status": "RISK_BLOCKED"
                    }
                }

            setup = self.trading_engine.generate_trade_setup(
                signal=signal,
                entry_price=current_price,
                risk_percent=self.config.risk_percent,
                risk_reward_ratio=self.config.risk_reward_ratio,
                balance=self.balance
            )

            if setup is not None:
                result = self.trading_engine.execute_trade_setup(
                    setup,
                    entry_timestamp=current_timestamp
                )

                position = self.trading_engine.trade_manager.position

                if position is not None:
                    self.agent_state.set_state("TRADING")

                    self.trade_history.add_trade({
                        "signal": signal,
                        "entry_price": setup["entry_price"],
                        "quantity": setup["quantity"],
                        "stop_loss": setup["stop_loss"],
                        "take_profit": setup["take_profit"],
                        "entry_timestamp": current_timestamp
                    })

                else:
                    self.agent_state.set_state("IDLE")

                return {
                    "signal": signal,
                    "position": position,
                    "result": result,
                    "setup": setup
                }

        self.agent_state.set_state("IDLE")

        return {
            "signal": signal,
            "position": None,
            "result": None
        }

    def get_statistics(self):
        statistics = self.trading_engine.get_statistics()

        return {
            "trades": statistics["total_trades"],
            "profit": statistics["total_profit"]
        }

    def run(self, candles):
        results = []
        history = []

        for candle in candles:
            history.append(candle)

            result = self.run_cycle(history)
            results.append(result)

        position = self.trading_engine.trade_manager.position

        if position is not None and candles:
            last_candle = candles[-1]

            if isinstance(last_candle, dict):
                final_price = last_candle["close"]
                final_timestamp = last_candle["timestamp"]
            else:
                final_price = last_candle.close
                final_timestamp = last_candle.timestamp

            close_result = self.trading_engine.trade_manager.close_position(
                exit_price=final_price,
                exit_timestamp=final_timestamp
            )

            if close_result is not None:
                self._process_closed_trade(close_result)

                results.append({
                    "signal": "CLOSE",
                    "position": None,
                    "result": close_result
                })

        return results

    def stop(self):
        self.agent_state.stop()
