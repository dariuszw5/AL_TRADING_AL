class StrategyEvaluator:

    def evaluate(self, summary):
        profit_factor = summary.get("profit_factor")
        expectancy = summary.get("expectancy")
        total_profit = summary.get("total_profit")
        max_drawdown = summary.get("max_drawdown")
        win_rate = summary.get("win_rate")
        trades = summary.get("trades", 0)

        if profit_factor is None:
            profit_factor = 0.0

        if expectancy is None:
            expectancy = 0.0

        if total_profit is None:
            total_profit = 0.0

        if max_drawdown is None:
            max_drawdown = 0.0

        if win_rate is None:
            win_rate = 0.0

        if trades is None:
            trades = 0

        if profit_factor == float("inf"):
            profit_factor = 10.0

        score = (
            total_profit
            + (profit_factor * 10.0)
            + (expectancy * 10.0)
            + (win_rate * 0.05)
            - (max_drawdown * 0.25)
        )

        if trades < 3:
            score *= 0.20
        elif trades < 5:
            score *= 0.40
        elif trades < 10:
            score *= 0.70
        elif trades < 15:
            score *= 0.85

        return float(score)