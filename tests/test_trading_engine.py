from src.trading.trading_engine import TradingEngine


def test_trading_engine_exists():
    engine = TradingEngine()

    assert engine is not None


def test_trading_engine_has_components():
    engine = TradingEngine()

    assert hasattr(engine, "strategy_engine")
    assert hasattr(engine, "trade_manager")


def test_process_buy_signal():
    engine = TradingEngine()

    result = engine.process_signal(
        signal="BUY",
        entry_price=100.0,
        quantity=2.0,
        stop_loss=95.0,
        take_profit=110.0
    )

    assert result["side"] == "BUY"
    assert result["entry_price"] == 100.0
    assert result["quantity"] == 2.0
    assert result["stop_loss"] == 95.0
    assert result["take_profit"] == 110.0
    assert engine.trade_manager.position is not None


def test_check_position_closes_on_take_profit():
    engine = TradingEngine()

    engine.process_signal(
        signal="BUY",
        entry_price=100.0,
        quantity=2.0,
        stop_loss=95.0,
        take_profit=110.0
    )

    result = engine.check_position(110.0)

    assert result["exit_price"] == 110.0
    assert result["profit"] == 20.0
    assert engine.trade_manager.position is None


def test_check_position_keeps_position_open():
    engine = TradingEngine()

    engine.process_signal(
        signal="BUY",
        entry_price=100.0,
        quantity=2.0,
        stop_loss=95.0,
        take_profit=110.0
    )

    result = engine.check_position(105.0)

    assert result is None
    assert engine.trade_manager.position is not None


def test_trading_engine_run():
    engine = TradingEngine()

    signals = [
        ("BUY", 100.0),
        ("HOLD", 105.0),
        ("HOLD", 109.0),
        ("HOLD", 110.0)
    ]

    result = engine.run(signals)

    assert result["trades"] == 1
    assert result["profit"] == 20.0


def test_trading_engine_run_uses_trade_parameters():
    engine = TradingEngine()

    signals = [
        ("BUY", 100.0),
        ("HOLD", 108.0),
        ("HOLD", 115.0)
    ]

    result = engine.run(
        signals,
        quantity=3.0,
        stop_loss=95.0,
        take_profit=115.0
    )

    assert result["trades"] == 1
    assert result["profit"] == 45.0


def test_trading_engine_generates_risk_levels():
    engine = TradingEngine()

    result = engine.generate_trade_setup(
        signal="BUY",
        entry_price=100.0,
        risk_percent=5.0,
        risk_reward_ratio=2.0
    )

    assert result is not None
    assert result["side"] == "BUY"
    assert result["entry_price"] == 100.0
    assert result["stop_loss"] is not None
    assert result["take_profit"] is not None
    assert result["quantity"] > 0


def test_trading_engine_processes_trade_setup():
    engine = TradingEngine()

    setup = engine.generate_trade_setup(
        signal="BUY",
        entry_price=100.0,
        risk_percent=5.0,
        risk_reward_ratio=2.0
    )

    result = engine.execute_trade_setup(setup)

    assert result is not None
    assert result["side"] == "BUY"
    assert result["entry_price"] == 100.0
    assert result["stop_loss"] is not None
    assert result["take_profit"] is not None
    assert engine.trade_manager.position is not None


def test_trading_engine_complete_trade_cycle():
    engine = TradingEngine()

    setup = engine.generate_trade_setup(
        signal="BUY",
        entry_price=100.0,
        risk_percent=5.0,
        risk_reward_ratio=2.0
    )

    engine.execute_trade_setup(setup)

    result = engine.check_position(setup["take_profit"])

    assert result is not None
    assert result["profit"] > 0
    assert engine.trade_manager.position is None


def test_trading_engine_complete_losing_trade():
    engine = TradingEngine()

    setup = engine.generate_trade_setup(
        signal="BUY",
        entry_price=100.0,
        risk_percent=5.0,
        risk_reward_ratio=2.0
    )

    engine.execute_trade_setup(setup)

    result = engine.check_position(setup["stop_loss"])

    assert result is not None
    assert result["profit"] < 0
    assert engine.trade_manager.position is None


def test_trading_engine_returns_statistics():
    engine = TradingEngine()

    setup = engine.generate_trade_setup(
        signal="BUY",
        entry_price=100.0,
        risk_percent=5.0,
        risk_reward_ratio=2.0
    )

    engine.execute_trade_setup(setup)
    engine.check_position(setup["take_profit"])

    statistics = engine.get_statistics()

    assert statistics["total_trades"] == 1
    assert statistics["winning_trades"] == 1
    assert statistics["losing_trades"] == 0
    assert statistics["win_rate"] == 100.0
    assert statistics["total_profit"] > 0


def test_trading_engine_paper_trading():
    engine = TradingEngine()

    assert hasattr(engine, "paper_trading")

    engine.paper_trading.open_position(
        side="BUY",
        entry_price=100.0,
        quantity=2.0,
        stop_loss=95.0,
        take_profit=110.0
    )

    result = engine.paper_trading.update_price(110.0)

    assert result is not None
    assert result["profit"] == 20.0


def test_trading_engine_paper_trading_cycle():
    engine = TradingEngine()

    engine.paper_trading.open_position(
        side="BUY",
        entry_price=100.0,
        quantity=2.0,
        stop_loss=95.0,
        take_profit=110.0
    )

    assert engine.paper_trading.position is not None

    result = engine.paper_trading.update_price(105.0)

    assert result is None
    assert engine.paper_trading.position is not None

    result = engine.paper_trading.update_price(110.0)

    assert result is not None
    assert result["profit"] == 20.0
    assert engine.paper_trading.position is None

