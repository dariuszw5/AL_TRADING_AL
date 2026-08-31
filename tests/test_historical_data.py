from src.data.historical_data import HistoricalData
from src.data.candle import Candle


def test_historical_data_has_candles():
    data = HistoricalData()

    assert hasattr(data, "candles")
    assert data.candles == []


def test_historical_data_can_save_csv(tmp_path):
    data = HistoricalData()

    candles = [
        Candle(
            timestamp=1,
            open=100.0,
            high=105.0,
            low=95.0,
            close=102.0,
            volume=10.0
        ),
        Candle(
            timestamp=2,
            open=102.0,
            high=108.0,
            low=100.0,
            close=106.0,
            volume=12.0
        )
    ]

    file_path = tmp_path / "candles.csv"

    data.save_csv(
        str(file_path),
        candles
    )

    assert file_path.exists()


def test_historical_data_can_load_csv(tmp_path):
    data = HistoricalData()

    candles = [
        Candle(
            timestamp=1,
            open=100.0,
            high=105.0,
            low=95.0,
            close=102.0,
            volume=10.0
        ),
        Candle(
            timestamp=2,
            open=102.0,
            high=108.0,
            low=100.0,
            close=106.0,
            volume=12.0
        )
    ]

    file_path = tmp_path / "candles.csv"

    data.save_csv(
        str(file_path),
        candles
    )

    loaded = data.load_csv(
        str(file_path)
    )

    assert len(loaded) == 2
    assert loaded[0].close == 102.0
    assert loaded[1].close == 106.0


def test_historical_data_count():
    data = HistoricalData()

    data.candles = [
        Candle(
            timestamp=1,
            open=100.0,
            high=105.0,
            low=95.0,
            close=102.0,
            volume=10.0
        )
    ]

    assert data.count() == 1