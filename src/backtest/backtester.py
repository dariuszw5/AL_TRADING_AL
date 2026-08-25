class Backtester:
    def __init__(self, initial_balance=0.0, fee_rate=0.0, position_size=None):
        self.initial_balance = initial_balance
        self.fee_rate = fee_rate
        self.position_size = position_size

    def run(self, signals):
        trades = 0
        profit = 0.0
        buy_price = None

        winning_trades = 0
        losing_trades = 0

        balance = self.initial_balance
        peak_balance = balance
        max_drawdown = 0.0

        for signal, price in signals:

            if signal == "BUY" and buy_price is None:
                if price <= 0:
                    continue

                buy_price = price

            elif signal == "SELL" and buy_price is not None:
                if price <= 0:
                    buy_price = None
                    continue

                if self.position_size is None:
                    quantity = 1.0
                else:
                    position_value = balance * self.position_size
                    quantity = position_value / buy_price

                buy_value = buy_price * quantity
                sell_value = price * quantity

                buy_fee = buy_value * self.fee_rate
                sell_fee = sell_value * self.fee_rate

                trade_profit = (
                    sell_value
                    - buy_value
                    - buy_fee
                    - sell_fee
                )

                trade_profit = round(trade_profit, 2)

                profit += trade_profit
                profit = round(profit, 2)

                balance += trade_profit
                balance = round(balance, 2)

                trades += 1

                if trade_profit > 0:
                    winning_trades += 1
                elif trade_profit < 0:
                    losing_trades += 1

                if balance > peak_balance:
                    peak_balance = balance

                if peak_balance > 0:
                    drawdown = (
                        (peak_balance - balance)
                        / peak_balance
                    ) * 100

                    if drawdown > max_drawdown:
                        max_drawdown = drawdown

                buy_price = None

        if self.initial_balance > 0:
            return_percent = (
                profit / self.initial_balance
            ) * 100
        else:
            return_percent = 0.0

        return_percent = round(return_percent, 2)

        if trades > 0:
            win_rate = round(
                (winning_trades / trades) * 100,
                2
            )
        else:
            win_rate = 0.0

        return {
            "trades": trades,
            "profit": profit,
            "balance": balance,
            "return_percent": return_percent,
            "return_percentage": return_percent,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": win_rate,
            "max_drawdown": round(max_drawdown, 2)
        }