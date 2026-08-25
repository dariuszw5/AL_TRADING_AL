from src.strategy.strategy_engine import StrategyEngine


def test_strategy_engine():
    engine = StrategyEngine()

    signal = engine.run()

    assert signal in ["BUY", "SELL", "HOLD"]