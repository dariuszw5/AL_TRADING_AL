from src.backtest.backtest_runner import BacktestRunner
from src.backtest.strategy_optimizer import StrategyOptimizer
from src.data.data_provider import DataProvider


VALIDATION_FILE = "data/backtest/BTCUSDT_1m_validation_5000.json"


def main():
    provider = DataProvider()

    candles = provider.load_candles(
        VALIDATION_FILE
    )

    optimizer = StrategyOptimizer()

    training_results = optimizer.run()

    validation_results = []

    print()
    print("=== VALIDATION OF ALL STRATEGIES ===")
    print()
    print(f"Validation data: {VALIDATION_FILE}")
    print(f"Świece:          {len(candles)}")
    print(f"Strategie:       {len(training_results)}")
    print()

    for index, training_result in enumerate(
        training_results,
        start=1
    ):
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

        runner.candles = candles

        runner.run()

        summary = runner.get_summary()

        validation_results.append(
            {
                "training_rank": index,
                "config": config,
                "training_result": training_result,
                "validation_summary": summary
            }
        )

    validation_results.sort(
        key=lambda result: result["validation_summary"]["total_profit"],
        reverse=True
    )

    print()
    print("=== VALIDATION RESULTS ===")
    print()

    print(
        f"{'Rank':<6}"
        f"{'Train':>7}"
        f"{'Method':<10}"
        f"{'Buy':>7}"
        f"{'Sell':>7}"
        f"{'Diff':>7}"
        f"{'Trades':>9}"
        f"{'Profit':>12}"
        f"{'PF':>10}"
        f"{'DD':>10}"
    )

    print("-" * 95)

    for rank, result in enumerate(
        validation_results,
        start=1
    ):
        config = result["config"]
        training_rank = result["training_rank"]
        summary = result["validation_summary"]

        profit_factor = summary["profit_factor"]

        if profit_factor == float("inf"):
            profit_factor_text = "inf"
        else:
            profit_factor_text = f"{profit_factor:.4f}"

        print(
            f"{rank:<6}"
            f"{training_rank:>7}"
            f"{config.rsi_method:<10}"
            f"{config.buy_rsi:>7.1f}"
            f"{config.sell_rsi:>7.1f}"
            f"{config.min_difference:>7.1f}"
            f"{summary['trades']:>9}"
            f"{summary['total_profit']:>12.4f}"
            f"{profit_factor_text:>10}"
            f"{summary['max_drawdown']:>10.4f}"
        )

    print()

    best = validation_results[0]

    config = best["config"]
    summary = best["validation_summary"]

    print("=== BEST VALIDATION STRATEGY ===")
    print()

    print(f"Training rank:    {best['training_rank']}")
    print(f"RSI method:       {config.rsi_method}")
    print(f"Buy RSI:          {config.buy_rsi}")
    print(f"Sell RSI:         {config.sell_rsi}")
    print(f"Min difference:   {config.min_difference}")
    print(f"Trading fee:      {config.trading_fee}")
    print()
    print(f"Trades:           {summary['trades']}")
    print(f"Total profit:     {summary['total_profit']:.4f}")
    print(f"Profit factor:    {summary['profit_factor']:.4f}")
    print(f"Win rate:         {summary['win_rate']:.4f}")
    print(f"Max drawdown:     {summary['max_drawdown']:.4f}")
    print(f"Expectancy:       {summary['expectancy']:.4f}")


if __name__ == "__main__":
    main()