from src.backtest.strategy_evaluator import StrategyEvaluator


def test_strategy_evaluator_returns_score():
    evaluator = StrategyEvaluator()

    summary = {
        "profit_factor": 1.5,
        "expectancy": 1.0,
        "total_profit": 20.0,
        "max_drawdown": 10.0,
        "win_rate": 60.0
    }

    score = evaluator.evaluate(summary)

    assert isinstance(score, float)


def test_profitable_strategy_scores_higher():
    evaluator = StrategyEvaluator()

    profitable = {
        "profit_factor": 1.5,
        "expectancy": 1.0,
        "total_profit": 20.0,
        "max_drawdown": 10.0,
        "win_rate": 60.0
    }

    losing = {
        "profit_factor": 0.8,
        "expectancy": -1.0,
        "total_profit": -20.0,
        "max_drawdown": 20.0,
        "win_rate": 50.0
    }

    profitable_score = evaluator.evaluate(profitable)
    losing_score = evaluator.evaluate(losing)

    assert profitable_score > losing_score


def test_strategy_evaluator_handles_none_values():
    evaluator = StrategyEvaluator()

    summary = {
        "profit_factor": None,
        "expectancy": None,
        "total_profit": None,
        "max_drawdown": None,
        "win_rate": None
    }

    score = evaluator.evaluate(summary)

    assert isinstance(score, float)


def test_infinite_profit_factor_does_not_create_infinite_score():
    evaluator = StrategyEvaluator()

    summary = {
        "profit_factor": float("inf"),
        "expectancy": 10.0,
        "total_profit": 10.0,
        "max_drawdown": 0.0,
        "win_rate": 100.0,
        "trades": 20
    }

    score = evaluator.evaluate(summary)

    assert score != float("inf")
    assert score > 0


def test_few_trades_are_penalized():
    evaluator = StrategyEvaluator()

    many_trades = {
        "profit_factor": 2.0,
        "expectancy": 1.0,
        "total_profit": 20.0,
        "max_drawdown": 5.0,
        "win_rate": 60.0,
        "trades": 20
    }

    few_trades = {
        "profit_factor": 2.0,
        "expectancy": 1.0,
        "total_profit": 20.0,
        "max_drawdown": 5.0,
        "win_rate": 60.0,
        "trades": 2
    }

    many_score = evaluator.evaluate(many_trades)
    few_score = evaluator.evaluate(few_trades)

    assert many_score > few_score