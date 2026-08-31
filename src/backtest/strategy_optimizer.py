from itertools import product

from src.backtest.backtest_runner import BacktestRunner
from src.backtest.optimization_result import OptimizationResult
from src.backtest.strategy_config import StrategyConfig
from src.backtest.strategy_evaluator import StrategyEvaluator
from src.data.data_provider import DataProvider


class StrategyOptimizer:

    TRAIN_FILE = "data/backtest/BTCUSDT_1m_5000.json"

    def __init__(
        self,
        buy_rsi_values=None,
        sell_rsi_values=None,
        min_difference_values=None,
        rsi_methods=None
    ):
        self.buy_rsi_values = (
            buy_rsi_values
            if buy_rsi_values is not None
            else [25.0, 30.0, 35.0]
        )

        self.sell_rsi_values = (
            sell_rsi_values
            if sell_rsi_values is not None
            else [65.0, 70.0, 75.0]
        )

        self.min_difference_values = (
            min_difference_values
            if min_difference_values is not None
            else [0.5, 1.0, 1.5, 2.0]
        )

        self.rsi_methods = (
            rsi_methods
            if rsi_methods is not None
            else ["classic", "wilder"]
        )

        self.evaluator = StrategyEvaluator()
        self.results = []

    def generate_configs(self):
        configs = []

        combinations = product(
            self.buy_rsi_values,
            self.sell_rsi_values,
            self.min_difference_values,
            self.rsi_methods
        )

        for (
            buy_rsi,
            sell_rsi,
            min_difference,
            rsi_method
        ) in combinations:

            if buy_rsi >= sell_rsi:
                continue

            configs.append(
                StrategyConfig(
                    buy_rsi=buy_rsi,
                    sell_rsi=sell_rsi,
                    min_difference=min_difference,
                    trading_fee=0.001,
                    rsi_method=rsi_method
                )
            )

        return configs

    def run(self):
        self.results = []

        configs = self.generate_configs()

        provider = DataProvider()

        candles = provider.load_candles(
            self.TRAIN_FILE
        )

        print()
        print("=== STRATEGY OPTIMIZATION ===")
        print()
        print(
            f"Training data: {self.TRAIN_FILE}"
        )
        print(
            f"Świece: {len(candles)}"
        )
        print(
            f"Strategie: {len(configs)}"
        )
        print()

        total = len(configs)

        for index, config in enumerate(configs, start=1):

            runner = BacktestRunner(
                symbol="BTCUSDT",
                interval="1m",
                limit=5000,
                initial_balance=1000.0,
                buy_rsi=config.buy_rsi,
                sell_rsi=config.sell_rsi,
                min_difference=config.min_difference,
                trading_fee=config.trading_fee,
                rsi_method=config.rsi_method,
                data_source="file"
            )

            runner.candles = candles

            runner.run()

            summary = runner.get_summary()

            score = self.evaluator.evaluate(summary)

            result = OptimizationResult(
                config=config,
                summary=summary,
                score=score
            )

            self.results.append(result)

            profit_factor = summary["profit_factor"]

            if profit_factor == float("inf"):
                profit_factor_text = "inf"
            else:
                profit_factor_text = f"{profit_factor:.4f}"

            print(
                f"[{index:02d}/{total}] "
                f"{config.rsi_method.capitalize():<7} "
                f"buy={config.buy_rsi:.1f} "
                f"sell={config.sell_rsi:.1f} "
                f"diff={config.min_difference:.1f} | "
                f"Trades={summary['trades']:<3} "
                f"Profit={summary['total_profit']:>9.4f} "
                f"PF={profit_factor_text:>8} "
                f"DD={summary['max_drawdown']:>8.4f} "
                f"Score={score:>10.4f}"
            )

        self.results.sort(
            key=lambda result: result.score,
            reverse=True
        )

        return self.results

    def get_results(self):
        return self.results

    def get_best_result(self):
        if not self.results:
            return None

        return self.results[0]