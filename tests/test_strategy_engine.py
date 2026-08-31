from src.strategy.strategy_engine import StrategyEngine


def test_strategy_engine():
    engine = StrategyEngine()

    signal = engine.run()

    assert signal in ["BUY", "SELL", "HOLD"]


def test_strategy_engine_has_risk_manager():
    engine = StrategyEngine()

    assert hasattr(engine, "risk_manager")



def test_strategy_engine_has_risk_levels():
    engine = StrategyEngine()

    assert hasattr(engine, "risk_levels")


def test_strategy_engine_calculates_risk_levels():
    engine = StrategyEngine()

    stop_loss = engine.risk_levels.calculate_stop_loss(
        entry_price=100.0,
        risk_percent=5.0
    )

    take_profit = engine.risk_levels.calculate_take_profit(
        entry_price=100.0,
        stop_loss=stop_loss,
        risk_reward_ratio=2.0
    )

    assert stop_loss == 95.0
    assert take_profit == 110.0


def test_strategy_engine_generates_trade_setup():
    engine = StrategyEngine()

    setup = engine.generate_trade_setup(
        signal="BUY",
        entry_price=100.0,
        risk_percent=5.0,
        risk_reward_ratio=2.0
    )

    assert setup["signal"] == "BUY"
    assert setup["entry_price"] == 100.0
    assert setup["stop_loss"] == 95.0
    assert setup["take_profit"] == 110.0