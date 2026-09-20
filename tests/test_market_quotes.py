from src.data.data_provider import DataProvider


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def test_binance_market_quote_uses_24h_ticker(monkeypatch):
    provider = DataProvider()

    monkeypatch.setattr(
        provider,
        "_get_binance",
        lambda endpoint, params: FakeResponse(
            {
                "symbol": "BTCUSDT",
                "lastPrice": "65000.00",
                "openPrice": "64000.00",
                "priceChange": "1000.00",
                "priceChangePercent": "1.5625",
                "highPrice": "66000.00",
                "lowPrice": "63000.00",
                "volume": "123.45",
                "quoteVolume": "8000000.00",
                "closeTime": 1_800_000_000_000,
            }
        ),
    )

    quote = provider.get_market_quote("BTCUSDT")

    assert quote["price"] == 65000.0
    assert quote["previous_close"] == 64000.0
    assert quote["change"] == 1000.0
    assert quote["change_pct"] == 1.5625
    assert quote["day_high"] == 66000.0
    assert quote["day_low"] == 63000.0
    assert quote["change_period"] == "24h"


def test_yahoo_market_quote_uses_previous_session_close(monkeypatch):
    provider = DataProvider()

    payload = {
        "chart": {
            "result": [
                {
                    "meta": {
                        "regularMarketPrice": 1.085,
                        "chartPreviousClose": 1.08,
                        "regularMarketDayHigh": 1.09,
                        "regularMarketDayLow": 1.075,
                        "regularMarketVolume": 123456,
                        "regularMarketTime": 1_800_000_000,
                    },
                    "timestamp": [
                        1_799_913_600,
                        1_800_000_000,
                    ],
                    "indicators": {
                        "quote": [
                            {
                                "open": [1.079, 1.081],
                                "high": [1.086, 1.09],
                                "low": [1.074, 1.075],
                                "close": [1.08, 1.085],
                                "volume": [100000, 123456],
                            }
                        ]
                    },
                }
            ],
            "error": None,
        }
    }

    monkeypatch.setattr(
        provider,
        "_request",
        lambda *args, **kwargs: FakeResponse(payload),
    )

    quote = provider.get_market_quote("EURUSD")

    assert quote["price"] == 1.085
    assert quote["previous_close"] == 1.08
    assert round(quote["change"], 6) == 0.005
    assert round(quote["change_pct"], 6) == round(
        (1.085 / 1.08 - 1.0) * 100.0,
        6,
    )
    assert quote["day_high"] == 1.09
    assert quote["day_low"] == 1.075
    assert quote["change_period"] == "sesja"
