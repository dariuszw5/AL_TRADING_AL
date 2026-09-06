from src.agent.agent_engine import AgentEngine
from src.backtest.backtest_engine import BacktestEngine


def test_backtest_engine_accepts_agent_engine():
    agent = AgentEngine()
    engine = BacktestEngine(agent)

    assert engine.agent is agent


def test_backtest_engine_runs_agent_cycles():
    agent = AgentEngine()
    engine = BacktestEngine(agent)

    candles = [
        {
            "timestamp": 1,
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 100.0,
            "volume": 1000.0
        },
        {
            "timestamp": 2,
            "open": 100.0,
            "high": 102.0,
            "low": 98.0,
            "close": 101.0,
            "volume": 1100.0
        },
        {
            "timestamp": 3,
            "open": 101.0,
            "high": 103.0,
            "low": 99.0,
            "close": 102.0,
            "volume": 1200.0
        }
    ]

    results = engine.run(candles)

    assert len(results) == 3


def test_backtest_engine_returns_agent_results():
    agent = AgentEngine()
    engine = BacktestEngine(agent)

    candles = [
        {
            "timestamp": 1,
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 100.0,
            "volume": 1000.0
        }
    ]

    results = engine.run(candles)

    assert isinstance(results, list)
    assert len(results) == 1
    assert isinstance(results[0], dict)
    assert "signal" in results[0]
def test_backtest_closes_short_on_intracandle_stop_loss():
    agent = AgentEngine()

    agent.analyze = lambda candles: {"signal": "SELL"}

    candles = [
        {
            "timestamp": 1,
            "open": 100.0,
            "high": 100.0,
            "low": 100.0,
            "close": 100.0,
            "volume": 1000.0
        },
        {
            "timestamp": 2,
            "open": 100.0,
            "high": 106.0,
            "low": 99.0,
            "close": 101.0,
            "volume": 1000.0
        }
    ]

    agent.trading_engine.generate_trade_setup = lambda **kwargs: {
        "side": "SELL",
        "entry_price": 100.0,
        "quantity": 1.0,
        "stop_loss": 105.0,
        "take_profit": 90.0
    }

    results = agent.run(candles)

    closed_trades = [
        result["result"]
        for result in results
        if isinstance(result, dict)
        and isinstance(result.get("result"), dict)
        and result["result"].get("exit_price") is not None
    ]

    assert len(closed_trades) == 1
    assert closed_trades[0]["exit_price"] == 105.0
    assert closed_trades[0]["profit"] == -5.0

def test_backtest_closes_open_position_at_end_of_data():
    agent = AgentEngine()

    agent.analyze = lambda candles: {"signal": "HOLD"}

    agent.trading_engine.process_signal(
        signal="BUY",
        entry_price=100.0,
        quantity=1.0,
        stop_loss=90.0,
        take_profit=110.0,
        entry_timestamp=1
    )

    engine = BacktestEngine(agent)

    candles = [
        {
            "timestamp": 1,
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 100.0,
            "volume": 1000.0
        },
        {
            "timestamp": 2,
            "open": 100.0,
            "high": 103.0,
            "low": 99.0,
            "close": 102.0,
            "volume": 1000.0
        }
    ]

    engine.run(candles)

    assert agent.trading_engine.trade_manager.position is None
    assert engine.get_trade_count() == 1
    assert engine.get_total_profit() == 2.0
