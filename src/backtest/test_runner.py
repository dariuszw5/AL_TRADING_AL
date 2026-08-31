from src.backtest.backtest_runner import BacktestRunner
from src.backtest.strategy_optimizer import StrategyOptimizer
from src.backtest.strategy_evaluator import StrategyEvaluator
from src.data.data_provider import DataProvider


TEST_FILE = "data/backtest/BTCUSDT_1m_test_5000.json"
VALIDATION_FILE = "data/backtest/BTCUSDT_1m_validation_5000.json"


def main():
    provider = DataProvider()
    evaluator = StrategyEvaluator()

    test_candles = provider.load_candles(TEST_FILE)
    validation_candles = provider.load_candles(VALIDATION_FILE)

    optimizer = StrategyOptimizer()
    training_results = optimizer.run()

    validation_results = []

    print()
    print("=== STRATEGY SELECTION ===")
    print()
    print("Training data:   data/backtest/BTCUSDT_1m_5000.json")
    print(f"Validation data: {VALIDATION_FILE}")
    print(f"Test data:       {TEST_FILE}")
    print()

    for training_result in training_results:
        config = training_result.config

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

        runner.candles = validation_candles
        runner.run()

        validation_summary = runner.get_summary()
        validation_score = evaluator.evaluate(
            validation_summary
        )

        validation_results.append(
            {
                "config": config,
                "training_result": training_result,
                "validation_summary": validation_summary,
                "validation_score": validation_score
            }
        )

    validation_results.sort(
        key=lambda result: result["validation_score"],
        reverse=True
    )

    best = validation_results[0]

    config = best["config"]
    training_result = best["training_result"]
    validation_summary = best["validation_summary"]
    validation_score = best["validation_score"]

    print("=== SELECTED STRATEGY ===")
    print()
    print(f"RSI method:        {config.rsi_method}")
    print(f"Buy RSI:           {config.buy_rsi}")
    print(f"Sell RSI:          {config.sell_rsi}")
    print(f"Min difference:    {config.min_difference}")
    print(f"Trading fee:       {config.trading_fee}")
    print()
    print(
        f"Training profit:   "
        f"{training_result.summary['total_profit']:.4f}"
    )
    print(
        f"Training score:    "
        f"{training_result.score:.4f}"
    )
    print(
        f"Validation profit: "
        f"{validation_summary['total_profit']:.4f}"
    )
    print(
        f"Validation score:  "
        f"{validation_score:.4f}"
    )

    test_runner = BacktestRunner(
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

    test_runner.candles = test_candles
    test_runner.run()

    test_summary = test_runner.get_summary()

    print()
    print("=== FINAL TEST ===")
    print()
    print(f"Test data:        {TEST_FILE}")
    print(f"Candles:          {len(test_candles)}")
    print()
    print(f"RSI method:       {config.rsi_method}")
    print(f"Buy RSI:          {config.buy_rsi}")
    print(f"Sell RSI:         {config.sell_rsi}")
    print(f"Min difference:   {config.min_difference}")
    print(f"Trading fee:      {config.trading_fee}")
    print()
    print(f"Trades:           {test_summary['trades']}")
    print(
        f"Total profit:     "
        f"{test_summary['total_profit']:.4f}"
    )
    print(
        f"Profit factor:    "
        f"{test_summary['profit_factor']:.4f}"
    )
    print(
        f"Win rate:         "
        f"{test_summary['win_rate']:.4f}"
    )
    print(
        f"Max drawdown:     "
        f"{test_summary['max_drawdown']:.4f}"
    )
    print(
        f"Expectancy:       "
        f"{test_summary['expectancy']:.4f}"
    )


if __name__ == "__main__":
    main()
