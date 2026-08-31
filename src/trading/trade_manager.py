class TradeManager:
    def __init__(self):
        self.position = None
        self.trade_history = []

    def open_position(
        self,
        side,
        entry_price,
        quantity,
        stop_loss,
        take_profit,
        entry_timestamp=None
    ):
        if self.position is not None:
            return None

        self.position = {
            "side": side,
            "entry_price": entry_price,
            "quantity": quantity,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "entry_timestamp": entry_timestamp
        }

        return self.position

    def close_position(
        self,
        exit_price,
        exit_timestamp=None
    ):
        if self.position is None:
            return None

        position = self.position

        if position["side"] == "BUY":
            profit = (
                exit_price - position["entry_price"]
            ) * position["quantity"]
        else:
            profit = (
                position["entry_price"] - exit_price
            ) * position["quantity"]

        result = {
            "side": position["side"],
            "entry_price": position["entry_price"],
            "exit_price": exit_price,
            "quantity": position["quantity"],
            "stop_loss": position["stop_loss"],
            "take_profit": position["take_profit"],
            "entry_timestamp": position["entry_timestamp"],
            "exit_timestamp": exit_timestamp,
            "profit": profit
        }

        self.trade_history.append(result)
        self.position = None

        return result

    def check_exit(self, current_price):
        if self.position is None:
            return None

        position = self.position

        if position["side"] == "BUY":
            if current_price <= position["stop_loss"]:
                return self.close_position(
                    exit_price=position["stop_loss"]
                )

            if current_price >= position["take_profit"]:
                return self.close_position(
                    exit_price=position["take_profit"]
                )

        elif position["side"] == "SELL":
            if current_price >= position["stop_loss"]:
                return self.close_position(
                    exit_price=position["stop_loss"]
                )

            if current_price <= position["take_profit"]:
                return self.close_position(
                    exit_price=position["take_profit"]
                )

        return None

    def get_statistics(self):
        total_trades = len(self.trade_history)

        winning_trades = sum(
            1
            for trade in self.trade_history
            if trade["profit"] > 0
        )

        losing_trades = sum(
            1
            for trade in self.trade_history
            if trade["profit"] < 0
        )

        total_profit = sum(
            trade["profit"]
            for trade in self.trade_history
        )

        if total_trades > 0:
            win_rate = (
                winning_trades / total_trades
            ) * 100
        else:
            win_rate = 0.0

        return {
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": win_rate,
            "total_profit": total_profit
        }