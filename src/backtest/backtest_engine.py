from src.backtest.backtest_result import BacktestResult


class BacktestEngine:

    def __init__(
        self,
        agent,
        initial_balance=1000.0,
        trading_fee=0.0
    ):
        self.agent = agent
        self.initial_balance = initial_balance
        self.trading_fee = float(trading_fee)
        self.results = []
        self.backtest_result = BacktestResult(
            initial_balance=initial_balance
        )
        self._history = []

    def _apply_trading_fee(self, trade):
        if not isinstance(trade, dict):
            return trade

        if "fee" in trade:
            return trade.copy()

        result = trade.copy()

        gross_profit = float(
            result.get("profit", 0.0)
        )

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

        result["gross_profit"] = gross_profit
        result["fee"] = fee
        result["profit"] = gross_profit - fee

        return result

    def run(self, candles):
        self.results = []
        self._history = []

        self.backtest_result = BacktestResult(
            initial_balance=self.initial_balance
        )

        for candle in candles:
            self._history.append(candle)

            result = self.agent.run_cycle(
                self._history
            )

            self.results.append(result)

            if not isinstance(result, dict):
                continue

            trade_result = result.get("result")

            if not isinstance(trade_result, dict):
                continue

            if "profit" not in trade_result:
                continue

            trade = self._apply_trading_fee(
                trade_result
            )

            self.backtest_result.add_trade(
                trade
            )

        return self.results

    def close(self, current_price):
        trading_engine = getattr(
            self.agent,
            "trading_engine",
            None
        )

        if trading_engine is None:
            return None

        trade_manager = getattr(
            trading_engine,
            "trade_manager",
            None
        )

        if trade_manager is None:
            return None

        if trade_manager.position is None:
            return None

        result = None

        check_position = getattr(
            trading_engine,
            "check_position",
            None
        )

        if check_position is not None:
            result = check_position(
                current_price
            )

        if result is None:
            result = trade_manager.close_position(
                exit_price=current_price
            )

        if isinstance(result, dict):
            if "profit" in result:
                trade = self._apply_trading_fee(
                    result
                )

                self.backtest_result.add_trade(
                    trade
                )

        return result

    def get_results(self):
        return self.results

    def get_backtest_result(self):
        return self.backtest_result

    def get_balance(self):
        return self.backtest_result.get_balance()

    def get_trade_count(self):
        return self.backtest_result.get_trade_count()

    def get_total_profit(self):
        return self.backtest_result.get_total_profit()

    def get_winning_trades(self):
        return self.backtest_result.get_winning_trades()

    def get_losing_trades(self):
        return self.backtest_result.get_losing_trades()

    def get_win_rate(self):
        return self.backtest_result.get_win_rate()

    def get_max_drawdown(self):
        return self.backtest_result.get_max_drawdown()

    def get_equity_curve(self):
        return self.backtest_result.get_equity_curve()
