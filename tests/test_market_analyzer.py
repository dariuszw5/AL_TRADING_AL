from src.analysis.market_analyzer import MarketAnalyzer


def test_market_analyzer():
    analyzer = MarketAnalyzer()

    result = analyzer.analyze()

    assert "sma" in result
    assert "ema" in result
    assert "rsi" in result