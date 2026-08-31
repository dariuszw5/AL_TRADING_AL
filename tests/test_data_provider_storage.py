import os

from src.data.data_provider import DataProvider
from src.data.candle import Candle


def create_candles():
    return [
        Candle(
            timestamp=1000,
            open=100.0,
            high=105.0,
            low=95.0,
            close=102.0,
            volume=10.0
        ),
        Candle(
            timestamp=1060,
            open=102.0,
            high=108.0,
            low=101.0,
            close=107.0,
            volume=12.0
        )
    ]


def test_data_provider_saves_candles(tmp_path):
    provider = DataProvider()

    candles = create_candles()
    file_path = tmp_path / "candles.json"

    provider.save_candles(
        candles,
        str(file_path)
    )

    assert file_path.exists()


def test_data_provider_loads_candles(tmp_path):
    provider = DataProvider()

    candles = create_candles()
    file_path = tmp_path / "candles.json"

    provider.save_candles(
        candles,
        str(file_path)
    )

    loaded = provider.load_candles(
        str(file_path)
    )

    assert len(loaded) == 2
    assert loaded[0].timestamp == 1000
    assert loaded[1].timestamp == 1060
    assert loaded[0].close == 102.0
    assert loaded[1].close == 107.0


def test_data_provider_loads_empty_file(tmp_path):
    provider = DataProvider()

    file_path = tmp_path / "candles.json"

    file_path.write_text(
        "[]",
        encoding="utf-8"
    )

    loaded = provider.load_candles(
        str(file_path)
    )

    assert loaded == []