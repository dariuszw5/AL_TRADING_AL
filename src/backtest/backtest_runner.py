from src.agent.agent_engine import AgentEngine
from src.agent.agent_config import AgentConfig
from src.backtest.backtest_engine import BacktestEngine
from src.data.data_provider import DataProvider


class BacktestRunner:

    def __init__(
        self,
        symbol="BTCUSDT",
        interval="1m",
        limit=1000,
        initial_balance=1000.0,
        buy_rsi=30.0,
        sell_rsi=70.0,
        min_difference=1.0,
        trading_fee=0.0,
        rsi_method="classic",
        data_source="api",
        data_file=None
    ):
        self.symbol = symbol
        self.interval = interval
        self.limit = limit
        self.initial_balance = initial_balance
        self.buy_rsi = buy_rsi
        self.sell_rsi = sell_rsi
        self.min_difference = min_difference
        self.trading_fee = float(trading_fee)
        self.rsi_method = rsi_method
        self.data_source = data_source

        if data_file is None:
            self.data_file = (
                f"data/backtest/"
                f"{self.symbol}_{self.interval}_5000.json"
            )
        else:
            self.data_file = data_file

        self.data_provider = DataProvider()

        self.agent = AgentEngine(
            config=AgentConfig(
                symbol=symbol,
                interval=interval,
                limit=limit,
                initial_balance=initial_balance,
                buy_rsi=buy_rsi,
                sell_rsi=sell_rsi,
                min_difference=min_difference,
                trading_fee=trading_fee,
                rsi_method=rsi_method
            )
        )

        self.backtest_engine = BacktestEngine(
            agent=self.agent,
            initial_balance=initial_balance,
            trading_fee=trading_fee
        )

        self.candles = []
        self.results = None

    def load_data(self):
        if self.data_source == "file":
            self.candles = self.data_provider.load_candles(
                self.data_file
            )
        else:
            self.candles = self.data_provider.get_historical_candles(
                symbol=self.symbol,
                interval=self.interval,
                limit=self.limit
            )

        return self.candles

    def run(self):
        if not self.candles:
            self.load_data()

        self.results = self.backtest_engine.run(
            self.candles
        )

        return self.results

    def get_backtest_result(self):
        return self.backtest_engine.get_backtest_result()

    def get_balance(self):
        return self.backtest_engine.get_balance()

    def get_total_profit(self):
        return self.backtest_engine.get_total_profit()

    def get_trade_count(self):
        return self.backtest_engine.get_trade_count()

    def get_winning_trades(self):
        return self.backtest_engine.get_winning_trades()

    def get_losing_trades(self):
        return self.backtest_engine.get_losing_trades()

    def get_win_rate(self):
        return self.backtest_engine.get_win_rate()

    def get_max_drawdown(self):
        return self.backtest_engine.get_max_drawdown()

    def get_equity_curve(self):
        return self.backtest_engine.get_equity_curve()

    def get_trades(self):
        return self.backtest_engine.get_backtest_result().get_trades()

    def get_profit_factor(self):
        return self.get_backtest_result().get_profit_factor()

    def get_average_win(self):
        return self.get_backtest_result().get_average_win()

    def get_average_loss(self):
        return self.get_backtest_result().get_average_loss()

    def get_largest_win(self):
        return self.get_backtest_result().get_largest_win()

    def get_largest_loss(self):
        return self.get_backtest_result().get_largest_loss()

    def get_expectancy(self):
        return self.get_backtest_result().get_expectancy()

    def get_summary(self):
        return {
            "symbol": self.symbol,
            "interval": self.interval,
            "candles": len(self.candles),
            "initial_balance": self.initial_balance,
            "final_balance": self.get_balance(),
            "trades": self.get_trade_count(),
            "winning_trades": self.get_winning_trades(),
            "losing_trades": self.get_losing_trades(),
            "win_rate": self.get_win_rate(),
            "total_profit": self.get_total_profit(),
            "max_drawdown": self.get_max_drawdown(),
            "profit_factor": self.get_profit_factor(),
            "average_win": self.get_average_win(),
            "average_loss": self.get_average_loss(),
            "largest_win": self.get_largest_win(),
            "largest_loss": self.get_largest_loss(),
            "expectancy": self.get_expectancy()
        }