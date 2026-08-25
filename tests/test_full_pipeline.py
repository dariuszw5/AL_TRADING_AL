from src.data.data_provider import DataProvider
from src.analysis.market_analyzer import MarketAnalyzer
from src.strategy.strategy_engine import StrategyEngine
from src.backtest.backtester import Backtester


def test_full_pipeline():
    provider = DataProvider()

    candles = provider.get_historical_candles(
        symbol="BTCUSDT",
        interval="1m",
        limit=500
    )

    assert len(candles) == 500

    analyzer = MarketAnalyzer()
    analyzed_data = analyzer.analyze(candles)

    engine = StrategyEngine()
    signals = engine.generate_signals(analyzed_data)

    assert len(signals) > 0

    backtester = Backtester(initial_balance=1000.0)
    result = backtester.run(signals)

    assert "trades" in result
    assert "profit" in result
    assert "return_percentage" in result