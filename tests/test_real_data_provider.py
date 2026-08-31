import pytest

from src.data.data_provider import DataProvider
from src.data.candle import Candle


def test_real_data_provider_returns_candles():
    provider = DataProvider()

    try:
        candles = provider.get_candles(
            symbol="BTCUSDT",
            interval="1m",
            limit=5
        )
    except Exception as error:
        pytest.skip(
            f"Binance API unavailable: {error}"
        )

    assert len(candles) == 5

    for candle in candles:
        assert isinstance(candle, Candle)


def test_real_data_provider_returns_valid_ohlcv():
    provider = DataProvider()

    try:
        candles = provider.get_candles(
            symbol="BTCUSDT",
            interval="1m",
            limit=5
        )
    except Exception as error:
        pytest.skip(
            f"Binance API unavailable: {error}"
        )

    for candle in candles:
        assert candle.timestamp > 0
        assert candle.open > 0
        assert candle.high > 0
        assert candle.low > 0
        assert candle.close > 0
        assert candle.volume >= 0

        assert candle.high >= candle.low


def test_real_data_provider_preserves_chronological_order():
    provider = DataProvider()

    try:
        candles = provider.get_candles(
            symbol="BTCUSDT",
            interval="1m",
            limit=10
        )
    except Exception as error:
        pytest.skip(
            f"Binance API unavailable: {error}"
        )

    timestamps = [
        candle.timestamp
        for candle in candles
    ]

    assert timestamps == sorted(timestamps)