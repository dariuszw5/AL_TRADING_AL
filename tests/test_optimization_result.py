from src.backtest.optimization_result import OptimizationResult
from src.backtest.strategy_config import StrategyConfig


def test_optimization_result_stores_data():
    config = StrategyConfig(
        buy_rsi=30.0,
        sell_rsi=70.0,
        min_difference=1.0,
        trading_fee=0.001,
        rsi_method="classic"
    )

    summary = {
        "total_profit": 10.0,
        "profit_factor": 1.3,
        "expectancy": 0.7,
        "max_drawdown": 15.0,
        "win_rate": 50.0
    }

    result = OptimizationResult(
        config=config,
        summary=summary,
        score=25.0
    )

    assert result.config is config
    assert result.summary is summary
    assert result.score == 25.0


def test_optimization_result_to_dict():
    config = StrategyConfig()

    summary = {
        "total_profit": 10.0
    }

    result = OptimizationResult(
        config=config,
        summary=summary,
        score=20.0
    )

    data = result.to_dict()

    assert data["config"]["buy_rsi"] == 30.0
    assert data["config"]["sell_rsi"] == 70.0
    assert data["summary"]["total_profit"] == 10.0
    assert data["score"] == 20.0