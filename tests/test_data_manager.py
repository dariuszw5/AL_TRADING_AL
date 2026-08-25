from src.data.data_manager import DataManager
from src.data.candle import Candle
import pytest


def test_add_candle():
    manager = DataManager()

    candle = Candle(
        timestamp=1000,
        open=100.0,
        high=110.0,
        low=95.0,
        close=105.0,
        volume=5000.0
    )

    manager.add_data(candle)

    assert manager.get_data() == [candle]


def test_candle():
    candle = Candle(
        timestamp=1000,
        open=100.0,
        high=110.0,
        low=95.0,
        close=105.0,
        volume=5000.0
    )

    assert candle.timestamp == 1000
    assert candle.open == 100.0
    assert candle.high == 110.0
    assert candle.low == 95.0
    assert candle.close == 105.0
    assert candle.volume == 5000.0


def test_add_invalid_data():
    manager = DataManager()

    with pytest.raises(TypeError):
        manager.add_data("BTC")