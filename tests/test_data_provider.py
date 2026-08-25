import pytest
import requests

from src.data.data_provider import DataProvider


def test_data_provider_exists():
    provider = DataProvider()

    assert provider is not None


def test_get_candles():
    provider = DataProvider()

    candles = provider.get_candles(
        symbol="BTCUSDT",
        interval="1m",
        limit=10
    )

    assert isinstance(candles, list)
    assert len(candles) == 10

def test_get_candles_returns_list():
    provider = DataProvider()

    candles = provider.get_candles()

    assert isinstance(candles, list)

    
def test_get_candles_api_error(monkeypatch):
    provider = DataProvider()

    class FakeResponse:
        def raise_for_status(self):
            raise requests.HTTPError("API error")

    def fake_get(*args, **kwargs):
        return FakeResponse()

    monkeypatch.setattr("requests.get", fake_get)

    with pytest.raises(requests.HTTPError):
        provider.get_candles()