import pytest

from src.data.data_provider import DataProvider
from src.agent.agent_engine import AgentEngine
from src.backtest.backtest_engine import BacktestEngine


def get_real_candles():
    provider = DataProvider()

    try:
        return provider.get_historical_candles(
            symbol="BTCUSDT",
            interval="1m",
            limit=50
        )
    except Exception as error:
        pytest.skip(
            f"Binance API unavailable: {error}"
        )


def test_real_backtest_uses_binance_data():
    candles = get_real_candles()

    assert len(candles) == 50


def test_real_backtest_runs_agent():
    candles = get_real_candles()

    agent = AgentEngine()
    backtest = BacktestEngine(
        agent=agent,
        initial_balance=1000.0
    )

    results = backtest.run(candles)

    assert isinstance(results, list)
    assert len(results) == len(candles)


def test_real_backtest_returns_result():
    candles = get_real_candles()

    agent = AgentEngine()
    backtest = BacktestEngine(
        agent=agent,
        initial_balance=1000.0
    )

    backtest.run(candles)

    result = backtest.get_backtest_result()

    assert result is not None
    assert backtest.get_balance() >= 0
    assert backtest.get_trade_count() >= 0
    assert backtest.get_total_profit() is not None
    assert backtest.get_win_rate() >= 0
    assert backtest.get_max_drawdown() >= 0