class Backtester:
    def __init__(self, initial_balance=0.0):
        self.initial_balance = initial_balance

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
                buy_price = price

            elif signal == "SELL" and buy_price is not None:
                trade_profit = price - buy_price

                profit += trade_profit
                balance += trade_profit
                trades += 1

                if trade_profit > 0:
                    winning_trades += 1
                elif trade_profit < 0:
                    losing_trades += 1

                if balance > peak_balance:
                    peak_balance = balance

                if peak_balance > 0:
                    drawdown = ((peak_balance - balance) / peak_balance) * 100

                    if drawdown > max_drawdown:
                        max_drawdown = drawdown

                buy_price = None

        if self.initial_balance > 0:
            return_percent = (profit / self.initial_balance) * 100
        else:
            return_percent = 0.0

        if trades > 0:
            win_rate = round((winning_trades / trades) * 100, 2)
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