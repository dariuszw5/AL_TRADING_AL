from src.backtest.strategy_config import StrategyConfig


def test_strategy_config_defaults():
    config = StrategyConfig()

    assert config.buy_rsi == 30.0
    assert config.sell_rsi == 70.0
    assert config.min_difference == 1.0
    assert config.trading_fee == 0.001
    assert config.rsi_method == "classic"


def test_strategy_config_accepts_custom_values():
    config = StrategyConfig(
        buy_rsi=25.0,
        sell_rsi=75.0,
        min_difference=1.5,
        trading_fee=0.002,
        rsi_method="wilder"
    )

    assert config.buy_rsi == 25.0
    assert config.sell_rsi == 75.0
    assert config.min_difference == 1.5
    assert config.trading_fee == 0.002
    assert config.rsi_method == "wilder"


def test_strategy_config_to_dict():
    config = StrategyConfig(
        buy_rsi=25.0,
        sell_rsi=75.0,
        min_difference=1.5,
        trading_fee=0.002,
        rsi_method="wilder"
    )

    result = config.to_dict()

    assert result["buy_rsi"] == 25.0
    assert result["sell_rsi"] == 75.0
    assert result["min_difference"] == 1.5
    assert result["trading_fee"] == 0.002
    assert result["rsi_method"] == "wilder"