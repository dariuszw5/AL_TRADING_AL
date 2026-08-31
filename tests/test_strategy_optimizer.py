from src.backtest.strategy_optimizer import StrategyOptimizer


def test_strategy_optimizer_generates_configs():
    optimizer = StrategyOptimizer()

    configs = optimizer.generate_configs()

    assert len(configs) == 72


def test_strategy_optimizer_generates_strategy_configs():
    optimizer = StrategyOptimizer(
        buy_rsi_values=[30.0],
        sell_rsi_values=[70.0],
        min_difference_values=[1.0],
        rsi_methods=["classic", "wilder"]
    )

    configs = optimizer.generate_configs()

    assert len(configs) == 2

    assert configs[0].buy_rsi == 30.0
    assert configs[0].sell_rsi == 70.0
    assert configs[0].min_difference == 1.0


def test_strategy_optimizer_skips_invalid_rsi_ranges():
    optimizer = StrategyOptimizer(
        buy_rsi_values=[70.0],
        sell_rsi_values=[30.0],
        min_difference_values=[1.0],
        rsi_methods=["classic"]
    )

    configs = optimizer.generate_configs()

    assert len(configs) == 0