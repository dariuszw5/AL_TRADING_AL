import pytest

from src.analysis.market_analyzer import MarketAnalyzer
from src.data.candle import Candle


def create_candles():
    prices = [
        100, 101, 102, 101, 103,
        104, 103, 105, 106, 105,
        107, 108, 107, 109, 110,
        108, 111, 112, 110, 113,
        114, 112, 115, 116, 114
    ]

    return [
        Candle(
            timestamp=i,
            open=price,
            high=price + 1,
            low=price - 1,
            close=price,
            volume=10.0
        )
        for i, price in enumerate(prices)
    ]


def test_market_analyzer_defaults_to_classic_rsi():
    analyzer = MarketAnalyzer()

    assert analyzer.rsi_method == "classic"


def test_market_analyzer_accepts_wilder_rsi():
    analyzer = MarketAnalyzer(
        rsi_method="wilder"
    )

    assert analyzer.rsi_method == "wilder"


def test_market_analyzer_rejects_invalid_rsi_method():
    with pytest.raises(ValueError):
        MarketAnalyzer(
            rsi_method="invalid"
        )


def test_market_analyzer_wilder_returns_rsi():
    analyzer = MarketAnalyzer(
        rsi_method="wilder"
    )

    result = analyzer.analyze(
        create_candles()
    )

    assert "rsi" in result
    assert result["rsi"]
    assert all(
        0 <= value <= 100
        for value in result["rsi"]
    )