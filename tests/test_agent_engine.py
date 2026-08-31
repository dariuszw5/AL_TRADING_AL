from src.agent.agent_engine import AgentEngine


def test_agent_engine_exists():
    engine = AgentEngine()

    assert engine is not None


def test_agent_engine_has_required_components():
    engine = AgentEngine()

    assert engine.data_provider is not None
    assert engine.data_manager is not None
    assert engine.strategy_engine is not None
    assert engine.trading_engine is not None


def test_agent_engine_has_paper_trading():
    engine = AgentEngine()

    assert engine.trading_engine.paper_trading is not None


def test_agent_engine_analyze():
    engine = AgentEngine()

    candles = [
        {
            "timestamp": 1,
            "open": 100.0,
            "high": 102.0,
            "low": 99.0,
            "close": 101.0,
            "volume": 10.0
        },
        {
            "timestamp": 2,
            "open": 101.0,
            "high": 104.0,
            "low": 100.0,
            "close": 103.0,
            "volume": 12.0
        },
        {
            "timestamp": 3,
            "open": 103.0,
            "high": 106.0,
            "low": 102.0,
            "close": 105.0,
            "volume": 15.0
        }
    ]

    result = engine.analyze(candles)

    assert result is not None
    assert "signal" in result


def test_agent_engine_trade_setup():
    engine = AgentEngine()

    result = engine.trading_engine.generate_trade_setup(
        signal="BUY",
        entry_price=100.0,
        risk_percent=5.0,
        risk_reward_ratio=2.0
    )

    assert result is not None
    assert result["side"] == "BUY"
    assert result["entry_price"] == 100.0
    assert result["stop_loss"] < 100.0
    assert result["take_profit"] > 100.0
    assert result["quantity"] > 0


def test_agent_engine_execute_trade():
    engine = AgentEngine()

    result = engine.execute_trade(
        signal="BUY",
        entry_price=100.0,
        quantity=2.0,
        stop_loss=95.0,
        take_profit=110.0
    )

    assert result is not None
    assert result["side"] == "BUY"
    assert result["entry_price"] == 100.0
    assert result["quantity"] == 2.0


def test_agent_engine_run_cycle():
    engine = AgentEngine()

    candles = [
        {
            "timestamp": 1,
            "open": 100.0,
            "high": 102.0,
            "low": 99.0,
            "close": 101.0,
            "volume": 10.0
        },
        {
            "timestamp": 2,
            "open": 101.0,
            "high": 104.0,
            "low": 100.0,
            "close": 103.0,
            "volume": 12.0
        },
        {
            "timestamp": 3,
            "open": 103.0,
            "high": 106.0,
            "low": 102.0,
            "close": 105.0,
            "volume": 15.0
        }
    ]

    result = engine.run_cycle(candles)

    assert result is not None
    assert "signal" in result
    assert "position" in result


def test_agent_engine_run_cycle_opens_buy_position():
    engine = AgentEngine()

    candles = [
        {
            "timestamp": 1,
            "open": 100.0,
            "high": 102.0,
            "low": 99.0,
            "close": 101.0,
            "volume": 10.0
        },
        {
            "timestamp": 2,
            "open": 101.0,
            "high": 104.0,
            "low": 100.0,
            "close": 103.0,
            "volume": 12.0
        },
        {
            "timestamp": 3,
            "open": 103.0,
            "high": 106.0,
            "low": 102.0,
            "close": 105.0,
            "volume": 15.0
        }
    ]

    engine.analyze = lambda candles: {"signal": "BUY"}

    result = engine.run_cycle(candles)

    assert result is not None
    assert result["signal"] == "BUY"
    assert result["position"] is not None


def test_agent_engine_run_cycle_closes_take_profit():
    engine = AgentEngine()

    engine.execute_trade(
        signal="BUY",
        entry_price=100.0,
        quantity=2.0,
        stop_loss=95.0,
        take_profit=110.0
    )

    candles = [
        {
            "timestamp": 1,
            "open": 108.0,
            "high": 111.0,
            "low": 107.0,
            "close": 110.0,
            "volume": 15.0
        }
    ]

    engine.analyze = lambda candles: {"signal": "HOLD"}

    result = engine.run_cycle(candles)

    assert result is not None
    assert result["result"] is not None
    assert result["result"]["profit"] == 20.0
    assert result["position"] is None


def test_agent_engine_statistics():
    engine = AgentEngine()

    result = engine.get_statistics()

    assert result is not None
    assert isinstance(result, dict)
    assert "trades" in result
    assert "profit" in result