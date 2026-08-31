from src.data.data_provider import DataProvider
from src.data.historical_data import HistoricalData
from src.data.candle import Candle


class FakeDataProvider(DataProvider):
    def get_historical_candles(
        self,
        symbol="BTCUSDT",
        interval="1m",
        limit=1000
    ):
        return [
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
            ),
            Candle(
                timestamp=3,
                open=106.0,
                high=110.0,
                low=103.0,
                close=109.0,
                volume=15.0
            )
        ]


def test_data_provider_returns_candles():
    provider = FakeDataProvider()

    candles = provider.get_historical_candles(
        symbol="BTCUSDT",
        interval="1m",
        limit=3
    )

    assert len(candles) == 3
    assert isinstance(candles[0], Candle)


def test_historical_data_can_save_provider_data(tmp_path):
    provider = FakeDataProvider()
    historical = HistoricalData()

    candles = provider.get_historical_candles(
        limit=3
    )

    file_path = tmp_path / "BTCUSDT_1m.csv"

    historical.save_csv(
        str(file_path),
        candles
    )

    assert file_path.exists()
    assert historical.count() == 3


def test_historical_data_can_reload_provider_data(tmp_path):
    provider = FakeDataProvider()
    historical = HistoricalData()

    candles = provider.get_historical_candles(
        limit=3
    )

    file_path = tmp_path / "BTCUSDT_1m.csv"

    historical.save_csv(
        str(file_path),
        candles
    )

    loaded = historical.load_csv(
        str(file_path)
    )

    assert len(loaded) == 3
    assert loaded[0].timestamp == 1
    assert loaded[0].close == 102.0
    assert loaded[-1].close == 109.0


def test_data_pipeline_preserves_ohlcv_data(tmp_path):
    provider = FakeDataProvider()
    historical = HistoricalData()

    candles = provider.get_historical_candles(
        limit=3
    )

    file_path = tmp_path / "BTCUSDT_1m.csv"

    historical.save_csv(
        str(file_path),
        candles
    )

    loaded = historical.load_csv(
        str(file_path)
    )

    candle = loaded[1]

    assert candle.timestamp == 2
    assert candle.open == 102.0
    assert candle.high == 108.0
    assert candle.low == 100.0
    assert candle.close == 106.0
    assert candle.volume == 12.0