from src.strategy.strategy_engine import StrategyEngine


def test_strategy_engine_uses_custom_balance():
    engine = StrategyEngine(initial_balance=1000.0)

    setup = engine.generate_trade_setup(
        signal="BUY",
        entry_price=100.0,
        risk_percent=5.0,
        risk_reward_ratio=2.0,
        balance=1200.0
    )

    assert setup["position_size"] == 12.0


def test_strategy_engine_uses_initial_balance_when_balance_is_not_given():
    engine = StrategyEngine(initial_balance=1000.0)

    setup = engine.generate_trade_setup(
        signal="BUY",
        entry_price=100.0,
        risk_percent=5.0,
        risk_reward_ratio=2.0
    )

    assert setup["position_size"] == 10.0
