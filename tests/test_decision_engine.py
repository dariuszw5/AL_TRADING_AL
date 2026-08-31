from src.agent.decision_engine import DecisionEngine


def test_decision_engine_exists():
    engine = DecisionEngine()

    assert engine is not None


def test_decision_engine_has_strategy_engine():
    engine = DecisionEngine()

    assert hasattr(engine, "strategy_engine")


def test_decision_engine_buy():
    engine = DecisionEngine()

    analysis = {
        "sma": [100.0],
        "ema": [105.0],
        "rsi": [25.0]
    }

    result = engine.decide(analysis)

    assert result == "BUY"


def test_decision_engine_sell():
    engine = DecisionEngine()

    analysis = {
        "sma": [105.0],
        "ema": [100.0],
        "rsi": [75.0]
    }

    result = engine.decide(analysis)

    assert result == "SELL"


def test_decision_engine_hold():
    engine = DecisionEngine()

    analysis = {
        "sma": [100.0],
        "ema": [100.0],
        "rsi": [50.0]
    }

    result = engine.decide(analysis)

    assert result == "HOLD"


def test_decision_engine_holds_when_rsi_is_not_extreme():
    engine = DecisionEngine()

    analysis = {
        "sma": [100.0],
        "ema": [105.0],
        "rsi": [50.0]
    }

    result = engine.decide(analysis)

    assert result == "HOLD"


def test_decision_engine_uses_trend_difference_filter():
    engine = DecisionEngine()

    analysis = {
        "sma": [100.0],
        "ema": [100.5],
        "rsi": [25.0]
    }

    result = engine.decide(analysis)

    assert result == "HOLD"