class BacktestResult:
    def __init__(self, initial_balance=1000.0):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.trades = []
        self.equity_curve = [initial_balance]

    def add_trade(self, trade):
        self.trades.append(trade)

        profit = trade.get("profit", 0.0)

        self.balance += profit
        self.equity_curve.append(self.balance)

    def get_balance(self):
        return self.balance

    def get_total_profit(self):
        return self.balance - self.initial_balance

    def get_trade_count(self):
        return len(self.trades)

    def get_trades(self):
        return self.trades.copy()

    def get_winning_trades(self):
        return sum(
            1
            for trade in self.trades
            if trade.get("profit", 0.0) > 0
        )

    def get_losing_trades(self):
        return sum(
            1
            for trade in self.trades
            if trade.get("profit", 0.0) < 0
        )

    def get_win_rate(self):
        total = self.get_trade_count()

        if total == 0:
            return 0.0

        return (
            self.get_winning_trades() / total
        ) * 100

    def get_profit_factor(self):
        gross_profit = sum(
            trade.get("profit", 0.0)
            for trade in self.trades
            if trade.get("profit", 0.0) > 0
        )

        gross_loss = sum(
            abs(trade.get("profit", 0.0))
            for trade in self.trades
            if trade.get("profit", 0.0) < 0
        )

        if gross_loss == 0:
            if gross_profit > 0:
                return float("inf")

            return 0.0

        return gross_profit / gross_loss

    def get_average_win(self):
        winning_trades = [
            trade.get("profit", 0.0)
            for trade in self.trades
            if trade.get("profit", 0.0) > 0
        ]

        if not winning_trades:
            return 0.0

        return sum(winning_trades) / len(winning_trades)

    def get_average_loss(self):
        losing_trades = [
            abs(trade.get("profit", 0.0))
            for trade in self.trades
            if trade.get("profit", 0.0) < 0
        ]

        if not losing_trades:
            return 0.0

        return sum(losing_trades) / len(losing_trades)

    def get_largest_win(self):
        winning_trades = [
            trade.get("profit", 0.0)
            for trade in self.trades
            if trade.get("profit", 0.0) > 0
        ]

        if not winning_trades:
            return 0.0

        return max(winning_trades)

    def get_largest_loss(self):
        losing_trades = [
            abs(trade.get("profit", 0.0))
            for trade in self.trades
            if trade.get("profit", 0.0) < 0
        ]

        if not losing_trades:
            return 0.0

        return max(losing_trades)

    def get_expectancy(self):
        total_trades = self.get_trade_count()

        if total_trades == 0:
            return 0.0

        total_profit = self.get_total_profit()

        return total_profit / total_trades

    def get_max_drawdown(self):
        if not self.equity_curve:
            return 0.0

        peak = self.equity_curve[0]
        max_drawdown = 0.0

        for equity in self.equity_curve:
            if equity > peak:
                peak = equity

            drawdown = peak - equity

            if drawdown > max_drawdown:
                max_drawdown = drawdown

        return max_drawdown

    def get_equity_curve(self):
        return self.equity_curve.copy()