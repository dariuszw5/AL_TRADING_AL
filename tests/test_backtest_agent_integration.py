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