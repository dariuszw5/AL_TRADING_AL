import requests

from src.agent.multi_asset_runner import MultiAssetPaperLive
from src.data.assets import SUPPORTED_ASSETS, get_asset
from src.data.data_provider import DataProvider


def test_supported_paper_assets_include_requested_markets():
    symbols = {asset.symbol for asset in SUPPORTED_ASSETS}

    assert {
        "BTCUSDT",
        "ETHUSDT",
        "SOLUSDT",
        "BNBUSDT",
        "XRPUSDT",
        "XAUUSD",
        "WTIUSD",
        "EURUSD",
        "AAPL",
    } <= symbols


def test_asset_lookup_is_case_insensitive():
    assert get_asset("ethusdt").provider_symbol == "ETHUSDT"
    assert get_asset("xauusd").provider == "yahoo"


def test_yahoo_candles_are_converted_to_candles(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "chart": {
                    "result": [
                        {
                            "timestamp": [1700000000, 1700000060],
                            "indicators": {
                                "quote": [
                                    {
                                        "open": [100, 101],
                                        "high": [102, 103],
                                        "low": [99, 100],
                                        "close": [101, 102],
                                        "volume": [10, 11],
                                    }
                                ]
                            },
                        }
                    ]
                }
            }

    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: FakeResponse())

    candles = DataProvider().get_candles(
        symbol="XAUUSD",
        interval="1m",
        limit=2,
    )

    assert len(candles) == 2
    assert candles[0].timestamp == 1700000000000
    assert candles[-1].close == 102.0


def test_multi_asset_runner_creates_isolated_loops():
    runner = MultiAssetPaperLive(
        assets=SUPPORTED_ASSETS[:2],
    )

    assert set(runner.loops) == {"BTCUSDT", "ETHUSDT"}
    assert runner.loops["BTCUSDT"].state_store.path.name == (
        "paper_live_BTCUSDT_1m.json"
    )
