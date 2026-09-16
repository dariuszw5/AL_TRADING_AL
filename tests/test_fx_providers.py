import json
from datetime import (
    date,
    datetime,
    timezone,
)
from pathlib import Path

import pytest

from src.core.clock import FixedClock
from src.fx.models import (
    FxSourceQuality,
)
from src.fx.providers import (
    CoinbaseUsdtUsdProvider,
    FxProviderError,
    NbpTableAProvider,
    YahooPlnProvider,
)


FIXTURES = (
    Path(__file__).parent
    / "fixtures"
    / "fx"
)

NOW = datetime(
    2026,
    9,
    16,
    18,
    0,
    tzinfo=timezone.utc,
)


def load_fixture(
    name,
):
    return json.loads(
        (
            FIXTURES
            / name
        ).read_text(
            encoding="utf-8-sig"
        )
    )


class FixtureJsonClient:

    def __init__(
        self,
        payload,
    ):
        self.payload = payload
        self.calls = []

    def get_json(
        self,
        url,
        *,
        timeout_seconds,
    ):
        self.calls.append(
            (
                url,
                timeout_seconds,
            )
        )

        return self.payload


def test_nbp_usd_reference_preserves_accounting_metadata():
    client = FixtureJsonClient(
        load_fixture(
            "nbp_usd.json"
        )
    )

    provider = NbpTableAProvider(
        json_client=client,
        clock=FixedClock(NOW),
    )

    quote = provider.get_reference(
        "USD"
    )

    assert quote.pair == "USDPLN"
    assert quote.rate == 3.7639

    assert (
        quote.source_quality
        is FxSourceQuality.DAILY_REFERENCE
    )

    assert quote.table == "180/A/NBP/2026"

    assert quote.effective_date == date(
        2026,
        9,
        16,
    )

    # NBP Table A does not expose a reliable
    # intraday publication timestamp.
    assert quote.provider_timestamp is None

    assert (
        "REFERENCE_ACCOUNTING_ONLY"
        in quote.labels
    )

    assert (
        "PUBLICATION_TIMESTAMP_UNAVAILABLE"
        in quote.labels
    )


def test_nbp_eur_reference():
    provider = NbpTableAProvider(
        json_client=FixtureJsonClient(
            load_fixture(
                "nbp_eur.json"
            )
        ),
        clock=FixedClock(NOW),
    )

    quote = provider.get_reference(
        "EUR"
    )

    assert quote.pair == "EURPLN"
    assert quote.rate == 4.3435


def test_nbp_date_specific_request_uses_requested_date():
    client = FixtureJsonClient(
        load_fixture(
            "nbp_usd.json"
        )
    )

    provider = NbpTableAProvider(
        json_client=client,
        clock=FixedClock(NOW),
    )

    quote = provider.get_reference(
        "USD",
        effective_date=date(
            2026,
            9,
            16,
        ),
    )

    assert (
        "/usd/2026-09-16/"
        in client.calls[0][0]
    )

    assert quote.effective_date == date(
        2026,
        9,
        16,
    )


def test_nbp_future_requested_date_is_rejected():
    provider = NbpTableAProvider(
        json_client=FixtureJsonClient(
            load_fixture(
                "nbp_usd.json"
            )
        ),
        clock=FixedClock(NOW),
    )

    with pytest.raises(
        ValueError,
        match="future NBP effective date",
    ):
        provider.get_reference(
            "USD",
            effective_date=date(
                2026,
                9,
                17,
            ),
        )


def test_nbp_does_not_support_arbitrary_currency():
    provider = NbpTableAProvider(
        json_client=FixtureJsonClient(
            load_fixture(
                "nbp_usd.json"
            )
        ),
        clock=FixedClock(NOW),
    )

    with pytest.raises(
        ValueError,
        match="unsupported NBP currency",
    ):
        provider.get_reference(
            "JPY"
        )


def test_yahoo_usdpln_is_always_stale_prone():
    client = FixtureJsonClient(
        load_fixture(
            "yahoo_usdpln.json"
        )
    )

    provider = YahooPlnProvider(
        json_client=client,
        clock=FixedClock(NOW),
    )

    quote = provider.get_quote(
        "USD"
    )

    assert quote.pair == "USDPLN"
    assert quote.rate == 3.7771

    assert (
        quote.source_quality
        is FxSourceQuality.STALE_PRONE
    )

    assert "UNOFFICIAL" in quote.labels
    assert "DEGRADED_BY_DESIGN" in quote.labels

    assert (
        "DELAY_METADATA_UNAVAILABLE"
        in quote.labels
    )

    assert (
        "PLN=X"
        in client.calls[0][0]
    )


def test_yahoo_zero_delay_metadata_does_not_upgrade_to_live():
    provider = YahooPlnProvider(
        json_client=FixtureJsonClient(
            load_fixture(
                "yahoo_eurpln.json"
            )
        ),
        clock=FixedClock(NOW),
    )

    quote = provider.get_quote(
        "EUR"
    )

    assert quote.pair == "EURPLN"

    assert (
        quote.source_quality
        is FxSourceQuality.STALE_PRONE
    )

    assert (
        "EXCHANGE_DATA_DELAYED_BY:0"
        in quote.labels
    )


def test_yahoo_provider_timestamp_is_utc():
    provider = YahooPlnProvider(
        json_client=FixtureJsonClient(
            load_fixture(
                "yahoo_usdpln.json"
            )
        ),
        clock=FixedClock(NOW),
    )

    quote = provider.get_quote(
        "USD"
    )

    assert quote.provider_timestamp is not None

    assert (
        quote.provider_timestamp.tzinfo
        is timezone.utc
    )


def test_coinbase_book_uses_real_midpoint():
    client = FixtureJsonClient(
        load_fixture(
            "coinbase_usdt_usd.json"
        )
    )

    provider = CoinbaseUsdtUsdProvider(
        json_client=client,
        clock=FixedClock(NOW),
    )

    quote = provider.get_quote()

    assert quote.pair == "USDTUSD"
    assert quote.bid == pytest.approx(
        0.99916
    )
    assert quote.ask == pytest.approx(
        0.99917
    )

    assert quote.rate == pytest.approx(
        (
            0.99916
            + 0.99917
        )
        / 2
    )

    assert (
        quote.source_quality
        is FxSourceQuality.LIVE
    )

    assert (
        "MIDPOINT_REFERENCE"
        in quote.labels
    )

    assert (
        "USDT-USD"
        in client.calls[0][0]
    )


def test_coinbase_timestamp_is_utc():
    provider = CoinbaseUsdtUsdProvider(
        json_client=FixtureJsonClient(
            load_fixture(
                "coinbase_usdt_usd.json"
            )
        ),
        clock=FixedClock(NOW),
    )

    quote = provider.get_quote()

    assert quote.provider_timestamp is not None

    assert (
        quote.provider_timestamp.tzinfo
        is timezone.utc
    )


def test_coinbase_missing_book_fails_closed():
    provider = CoinbaseUsdtUsdProvider(
        json_client=FixtureJsonClient(
            {
                "bids": [],
                "asks": [],
                "time": (
                    "2026-09-16T17:41:08Z"
                ),
            }
        ),
        clock=FixedClock(NOW),
    )

    with pytest.raises(
        FxProviderError,
        match="COINBASE_BOOK_UNAVAILABLE",
    ):
        provider.get_quote()


def test_coinbase_missing_provider_time_fails_closed():
    provider = CoinbaseUsdtUsdProvider(
        json_client=FixtureJsonClient(
            {
                "bids": [
                    [
                        "0.999",
                        "1",
                        "1",
                    ]
                ],
                "asks": [
                    [
                        "1.001",
                        "1",
                        "1",
                    ]
                ],
            }
        ),
        clock=FixedClock(NOW),
    )

    with pytest.raises(
        FxProviderError,
        match="COINBASE_PROVIDER_TIMESTAMP_UNAVAILABLE",
    ):
        provider.get_quote()
