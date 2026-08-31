class BacktestReport:
    def __init__(self, runner):
        self.runner = runner

    def get_data(self):
        return self.runner.get_summary()

    def get_trades(self):
        return self.runner.get_trades()

    def format(self):
        data = self.get_data()

        profit = data["total_profit"]

        return (
            "================================\n"
            "       BACKTEST REPORT\n"
            "================================\n\n"
            f"Symbol:              {data['symbol']}\n"
            f"Interwał:            {data['interval']}\n"
            f"Liczba świec:        {data['candles']}\n\n"
            f"Saldo początkowe:    "
            f"{data['initial_balance']:.2f}\n"
            f"Saldo końcowe:       "
            f"{data['final_balance']:.2f}\n"
            f"Zysk / strata:       "
            f"{profit:.2f}\n\n"
            f"Liczba transakcji:   {data['trades']}\n"
            f"Wygrane:             {data['winning_trades']}\n"
            f"Przegrane:           {data['losing_trades']}\n"
            f"Win rate:            "
            f"{data['win_rate']:.2f}%\n\n"
            f"Profit Factor:       "
            f"{data['profit_factor']:.2f}\n"
            f"Average Win:         "
            f"{data['average_win']:.2f}\n"
            f"Average Loss:        "
            f"{data['average_loss']:.2f}\n"
            f"Largest Win:         "
            f"{data['largest_win']:.2f}\n"
            f"Largest Loss:        "
            f"{data['largest_loss']:.2f}\n"
            f"Expectancy:          "
            f"{data['expectancy']:.2f}\n\n"
            f"Max drawdown:        "
            f"{data['max_drawdown']:.2f}\n\n"
            "================================"
        )

    def format_trades(self):
        trades = self.get_trades()

        lines = [
            "============================================================",
            "                    TRADE HISTORY",
            "============================================================",
            "",
            "Nr | Side | Entry | Exit | Quantity | P/L | Entry Time | Exit Time",
            "---+------+-------+------+----------+-----+------------+----------"
        ]

        for index, trade in enumerate(trades, start=1):
            side = trade.get("side", "")
            entry_price = trade.get("entry_price", 0.0)
            exit_price = trade.get("exit_price", 0.0)
            quantity = trade.get("quantity", 0.0)
            profit = trade.get("profit", 0.0)
            entry_timestamp = trade.get("entry_timestamp")
            exit_timestamp = trade.get("exit_timestamp")

            lines.append(
                f"{index:>2} | "
                f"{side:<4} | "
                f"{entry_price:>5.2f} | "
                f"{exit_price:>4.2f} | "
                f"{quantity:>8.2f} | "
                f"{profit:>5.2f} | "
                f"{str(entry_timestamp):>10} | "
                f"{str(exit_timestamp):>8}"
            )

        lines.append("")
        lines.append("============================================================")

        return "\n".join(lines)

    def print_report(self):
        print(self.format())

    def print_trades(self):
        print(self.format_trades())