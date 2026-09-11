from src.strategy.strategy_engine import StrategyEngine
from src.trading.trade_manager import TradeManager
from src.trading.paper_trading import PaperTrading


class TradingEngine:
    def __init__(self, strategy_engine=None):
        self.strategy_engine = (
            strategy_engine
            if strategy_engine is not None
            else StrategyEngine()
        )
        self.trade_manager = TradeManager()
        self.paper_trading = PaperTrading()
        self.trade_result_callback = None

    def set_trade_result_callback(self, callback):
        self.trade_result_callback = callback

    def process_signal(
        self,
        signal,
        entry_price,
        quantity,
        stop_loss,
        take_profit,
        entry_timestamp=None
    ):
        if signal not in ("BUY", "SELL"):
            return None

        return self.trade_manager.open_position(
            side=signal,
            entry_price=entry_price,
            quantity=quantity,
            stop_loss=stop_loss,
            take_profit=take_profit,
            entry_timestamp=entry_timestamp
        )

    def check_position(
        self,
        current_price,
        exit_timestamp=None
    ):
        result = self.trade_manager.check_exit(
            current_price
        )

        if result is not None:
            result["exit_timestamp"] = exit_timestamp

            if self.trade_result_callback is not None:
                self.trade_result_callback(result)

        return result

    def check_candle(
        self,
        high,
        low,
        close,
        timestamp=None
    ):
        position = self.trade_manager.position

        if position is None:
            return None

        side = position["side"]
        stop_loss = position["stop_loss"]
        take_profit = position["take_profit"]

        exit_price = None
        exit_reason = None

        if side == "BUY":

            if low <= stop_loss:
                exit_price = stop_loss
                exit_reason = "STOP_LOSS"

            elif high >= take_profit:
                exit_price = take_profit
                exit_reason = "TAKE_PROFIT"

        elif side == "SELL":

            if high >= stop_loss:
                exit_price = stop_loss
                exit_reason = "STOP_LOSS"

            elif low <= take_profit:
                exit_price = take_profit
                exit_reason = "TAKE_PROFIT"

        if exit_price is None:
            return None

        result = self.trade_manager.close_position(
            exit_price=exit_price,
            exit_timestamp=timestamp
        )

        if result is not None:

            result["exit_reason"] = exit_reason

            if self.trade_result_callback is not None:
                self.trade_result_callback(result)

        return result

    def run(
        self,
        signals,
        quantity=2.0,
        stop_loss=95.0,
        take_profit=110.0
    ):
        trades = 0
        profit = 0.0

        for signal, price in signals:

            if self.trade_manager.position is None:

                if signal in ("BUY", "SELL"):

                    self.process_signal(
                        signal=signal,
                        entry_price=price,
                        quantity=quantity,
                        stop_loss=stop_loss,
                        take_profit=take_profit
                    )

            else:

                result = self.check_position(price)

                if result is not None:
                    trades += 1
                    profit += result["profit"]

        return {
            "trades": trades,
            "profit": profit
        }

    def generate_trade_setup(
        self,
        signal,
        entry_price,
        risk_percent,
        risk_reward_ratio,
        balance=None,
        stop_loss_percent=None,
        max_exposure_percent=None
    ):
        setup = self.strategy_engine.generate_trade_setup(
            signal=signal,
            entry_price=entry_price,
            risk_percent=risk_percent,
            stop_loss_percent=stop_loss_percent,
            risk_reward_ratio=risk_reward_ratio,
            balance=balance,
            max_exposure_percent=max_exposure_percent
        )

        if setup is None:
            return None

        setup["side"] = signal

        if "quantity" not in setup:

            if "position_size" in setup:
                setup["quantity"] = setup["position_size"]

        return setup

    def execute_trade_setup(
        self,
        setup,
        entry_timestamp=None
    ):
        if setup is None:
            return None

        return self.process_signal(
            signal=setup["side"],
            entry_price=setup["entry_price"],
            quantity=setup["quantity"],
            stop_loss=setup["stop_loss"],
            take_profit=setup["take_profit"],
            entry_timestamp=entry_timestamp
        )

    def get_statistics(self):
        return self.trade_manager.get_statistics()
