from src.backtest.backtest_result import BacktestResult


class BacktestEngine:

    def __init__(
        self,
        agent,
        initial_balance=1000.0,
        trading_fee=0.0
    ):
        self.agent = agent
        self.initial_balance = float(initial_balance)
        self.trading_fee = float(trading_fee)

        self.results = []
        self._history = []

        self.backtest_result = BacktestResult(
            initial_balance=self.initial_balance
        )

    def _get_trade_manager(self):
        trading_engine = getattr(
            self.agent,
            "trading_engine",
            None
        )

        if trading_engine is None:
            return None

        return getattr(
            trading_engine,
            "trade_manager",
            None
        )

    def _get_candle_close(self, candle):
        if isinstance(candle, dict):
            return float(candle["close"])

        return float(candle.close)

    def _get_candle_timestamp(self, candle):
        if isinstance(candle, dict):
            return candle.get("timestamp")

        return getattr(
            candle,
            "timestamp",
            None
        )

    def _apply_trading_fee(self, trade):
        if not isinstance(trade, dict):
            return trade

        result = trade.copy()

        if "profit" not in result:
            return result

        if (
            "gross_profit" in result
            and "fee" in result
        ):
            return result

        entry_price = float(
            result.get("entry_price", 0.0)
        )

        exit_price = float(
            result.get("exit_price", 0.0)
        )

        quantity = float(
            result.get("quantity", 0.0)
        )

        gross_profit = float(
            result["profit"]
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

    def _process_closed_trade(self, trade):
        if not isinstance(trade, dict):
            return None

        if "profit" not in trade:
            return None

        processed_trade = self._apply_trading_fee(
            trade
        )

        self.backtest_result.add_trade(
            processed_trade
        )

        return processed_trade

    def _process_agent_closed_trade(self, trade):
        if not isinstance(trade, dict):
            return None

        if "profit" not in trade:
            return None

        processor = getattr(
            self.agent,
            "_process_closed_trade",
            None
        )

        if processor is None:
            return trade

        processor(trade)

        return trade

    def _close_trade_manager_position(
        self,
        trade_manager,
        exit_price,
        exit_timestamp=None
    ):
        if trade_manager is None:
            return None

        if exit_timestamp is not None:
            try:
                return trade_manager.close_position(
                    exit_price=exit_price,
                    exit_timestamp=exit_timestamp
                )
            except TypeError:
                pass

        return trade_manager.close_position(
            exit_price=exit_price
        )

    def _auto_close_last_position(self, candles):
        if not candles:
            return None

        trade_manager = self._get_trade_manager()

        if trade_manager is None:
            return None

        position = getattr(
            trade_manager,
            "position",
            None
        )

        if position is None:
            return None

        last_candle = candles[-1]

        final_price = self._get_candle_close(
            last_candle
        )

        final_timestamp = self._get_candle_timestamp(
            last_candle
        )

        close_result = self._close_trade_manager_position(
            trade_manager=trade_manager,
            exit_price=final_price,
            exit_timestamp=final_timestamp
        )

        if close_result is None:
            return None

        if not isinstance(close_result, dict):
            return close_result

        if "exit_reason" not in close_result:
            close_result["exit_reason"] = (
                "END_OF_DATA"
            )

        processed_trade = (
            self._process_agent_closed_trade(
                close_result
            )
        )

        if processed_trade is None:
            return None

        return self._process_closed_trade(
            processed_trade
        )

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

            self._process_closed_trade(
                trade_result
            )

        if candles:
            self._auto_close_last_position(
                candles
            )

        return self.results

    def close(self, price, timestamp=None):
        trade_manager = self._get_trade_manager()

        if trade_manager is None:
            return None

        position = getattr(
            trade_manager,
            "position",
            None
        )

        if position is None:
            return None

        close_result = self._close_trade_manager_position(
            trade_manager=trade_manager,
            exit_price=float(price),
            exit_timestamp=timestamp
        )

        if close_result is None:
            return None

        if not isinstance(close_result, dict):
            return close_result

        if "exit_reason" not in close_result:
            close_result["exit_reason"] = (
                "MANUAL_CLOSE"
            )

        processed_trade = (
            self._process_agent_closed_trade(
                close_result
            )
        )

        if processed_trade is None:
            return None

        return self._process_closed_trade(
            processed_trade
        )

    def get_backtest_result(self):
        return self.backtest_result

    def get_balance(self):
        return self.backtest_result.get_final_balance()

    def get_trades(self):
        return self.backtest_result.get_trades()

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

    def get_profit_factor(self):
        return self.backtest_result.get_profit_factor()

    def get_average_win(self):
        return self.backtest_result.get_average_win()

    def get_average_loss(self):
        return self.backtest_result.get_average_loss()

    def get_largest_win(self):
        return self.backtest_result.get_largest_win()

    def get_largest_loss(self):
        return self.backtest_result.get_largest_loss()

    def get_expectancy(self):
        return self.backtest_result.get_expectancy()

    def get_max_drawdown(self):
        return self.backtest_result.get_max_drawdown()

    def get_equity_curve(self):
        return self.backtest_result.get_equity_curve()