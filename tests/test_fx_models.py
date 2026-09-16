from datetime import (
    date,
    datetime,
    timezone,
)

import pytest

from src.fx.models import (
    FxFreshness,
    FxPath,
    FxQuote,
    FxSourceQuality,
)


NOW = datetime(
    2026,
    9,
    16,
    17,
    0,
    tzinfo=timezone.utc,
)


def test_fx_path_preserves_route():
    path = FxPath(
        (
            "USDT",
            "USD",
            "PLN",
        )
    )

    assert path.currencies == (
        "USDT",
        "USD",
        "PLN",
    )

    assert path.text == "USDT→USD→PLN"


def test_fx_path_normalizes_currency_codes():
    path = FxPath(
        (
            "usdt",
            "usd",
            "pln",
        )
    )

    assert path.currencies == (
        "USDT",
        "USD",
        "PLN",
    )


def test_fx_quote_preserves_nbp_metadata():
    quote = FxQuote(
        base_currency="USD",
        quote_currency="PLN",
        rate=3.7639,
        provider="NBP",
        provider_timestamp=NOW,
        observed_at=NOW,
        source_quality=(
            FxSourceQuality.DAILY_REFERENCE
        ),
        table="180/A/NBP/2026",
        effective_date=date(
            2026,
            9,
            16,
        ),
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


def test_fx_quote_normalizes_timestamp_to_utc():
    quote = FxQuote(
        base_currency="USD",
        quote_currency="PLN",
        rate=3.7,
        provider="TEST",
        provider_timestamp=NOW,
        observed_at=NOW,
        source_quality=(
            FxSourceQuality.LIVE
        ),
    )

    assert (
        quote.provider_timestamp.utcoffset()
        == timezone.utc.utcoffset(NOW)
    )

    assert (
        quote.observed_at.utcoffset()
        == timezone.utc.utcoffset(NOW)
    )


def test_fx_quote_rejects_non_positive_rate():
    with pytest.raises(
        ValueError,
        match="rate must be positive",
    ):
        FxQuote(
            base_currency="USD",
            quote_currency="PLN",
            rate=0.0,
            provider="TEST",
            provider_timestamp=NOW,
            observed_at=NOW,
            source_quality=(
                FxSourceQuality.LIVE
            ),
        )


def test_fx_quote_rejects_crossed_book():
    with pytest.raises(
        ValueError,
        match="bid cannot exceed ask",
    ):
        FxQuote(
            base_currency="USDT",
            quote_currency="USD",
            rate=1.0,
            provider="TEST",
            provider_timestamp=NOW,
            observed_at=NOW,
            source_quality=(
                FxSourceQuality.LIVE
            ),
            bid=1.01,
            ask=1.00,
        )


def test_source_quality_and_freshness_are_distinct():
    assert (
        FxSourceQuality.STALE_PRONE.value
        == "STALE_PRONE"
    )

    assert (
        FxFreshness.FX_FRESH.value
        == "FX_FRESH"
    )
