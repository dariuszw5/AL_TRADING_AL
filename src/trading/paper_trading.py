from src.trading.trade_manager import TradeManager


class PaperTrading:
    def __init__(self, initial_balance=1000.0):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.equity = initial_balance
        self.trade_manager = TradeManager()

    @property
    def position(self):
        return self.trade_manager.position

    def open_position(
        self,
        side,
        entry_price,
        quantity,
        stop_loss,
        take_profit
    ):
        return self.trade_manager.open_position(
            side=side,
            entry_price=entry_price,
            quantity=quantity,
            stop_loss=stop_loss,
            take_profit=take_profit
        )

    def update_price(self, current_price):
        if self.position is None:
            self.equity = self.balance
            return None

        position = self.position

        if position["side"] == "BUY":
            unrealized_profit = (
                current_price - position["entry_price"]
            ) * position["quantity"]
        else:
            unrealized_profit = (
                position["entry_price"] - current_price
            ) * position["quantity"]

        self.equity = self.balance + unrealized_profit

        result = self.trade_manager.check_exit(current_price)

        if result is not None:
            self.balance += result["profit"]
            self.equity = self.balance

        return result