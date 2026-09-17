from datetime import (
    date,
    datetime,
    timedelta,
    timezone,
)
import threading

import pytest

from src.accounting.production_fx_scheduler import (
    FX_PREFETCH_TIMEOUT,
    PREVIOUS_FX_PREFETCH_STILL_RUNNING,
    ParallelProductionFxResolver,
    ProductionFxSchedulerError,
)
from src.fx.models import (
    FxQuote,
    FxSourceQuality,
)


UTC = timezone.utc

NOW = datetime(
    2026,
    9,
    17,
    12,
    0,
    tzinfo=UTC,
)


class FixedClock:
    def now(self):
        return NOW


class BarrierProviderBase:
    def __init__(
        self,
        barrier,
    ):
        self.barrier = barrier
        self.calls = 0

    def rendezvous(self):
        self.calls += 1
        self.barrier.wait(
            timeout=2.0
        )


class BarrierYahoo(
    BarrierProviderBase
):
    def get_quote(
        self,
        base_currency,
    ):
        self.rendezvous()

        return FxQuote(
            base_currency=(
                str(base_currency)
                .upper()
            ),
            quote_currency="PLN",
            rate=4.0,
            provider=(
                "YAHOO_FINANCE_V8_CHART"
            ),
            provider_timestamp=(
                NOW
                - timedelta(
                    seconds=10
                )
            ),
            observed_at=NOW,
            source_quality=(
                FxSourceQuality.STALE_PRONE
            ),
            labels=(
                "UNOFFICIAL",
                "DEGRADED_BY_DESIGN",
            ),
        )


class BarrierNbp(
    BarrierProviderBase
):
    def get_reference(
        self,
        currency,
        *,
        effective_date=None,
    ):
        self.rendezvous()

        return FxQuote(
            base_currency=(
                str(currency)
                .upper()
            ),
            quote_currency="PLN",
            rate=3.9,
            provider="NBP_TABLE_A",
            provider_timestamp=None,
            observed_at=NOW,
            source_quality=(
                FxSourceQuality.DAILY_REFERENCE
            ),
            table="181/A/NBP/2026",
            effective_date=date(
                2026,
                9,
                17,
            ),
        )


class BarrierCoinbase(
    BarrierProviderBase
):
    def get_quote(self):
        self.rendezvous()

        return FxQuote(
            base_currency="USDT",
            quote_currency="USD",
            rate=0.999,
            provider="COINBASE_EXCHANGE",
            provider_timestamp=(
                NOW
                - timedelta(
                    seconds=5
                )
            ),
            observed_at=NOW,
            source_quality=(
                FxSourceQuality.LIVE
            ),
            bid=0.9989,
            ask=0.9991,
        )


def parallel_resolver(
    *,
    barrier,
    timeout=1.0,
    workers=3,
):
    return (
        ParallelProductionFxResolver(
            prefetch_timeout_seconds=(
                timeout
            ),
            max_workers=workers,
            clock=FixedClock(),
            yahoo_provider=(
                BarrierYahoo(
                    barrier
                )
            ),
            nbp_provider=(
                BarrierNbp(
                    barrier
                )
            ),
            coinbase_provider=(
                BarrierCoinbase(
                    barrier
                )
            ),
        )
    )


def test_btc_required_fx_sources_start_concurrently():
    barrier = threading.Barrier(
        3
    )

    resolver = parallel_resolver(
        barrier=barrier,
        timeout=1.0,
        workers=3,
    )

    resolver.begin_cycle(
        [
            "BTCUSDT",
        ]
    )

    assert resolver.provider_errors == {}

    assert {
        quote.pair
        for quote
        in resolver.mtm_quotes
    } == {
        "USDPLN",
        "USDTUSD",
    }

    assert {
        quote.pair
        for quote
        in resolver.realized_quotes
    } == {
        "USDPLN",
        "USDTUSD",
    }

    assert (
        resolver.last_prefetch_timed_out
        is False
    )

    assert (
        resolver.last_prefetch_duration_seconds
        is not None
    )


class BlockingProviderBase:
    def __init__(
        self,
        *,
        started,
        release,
    ):
        self.started = started
        self.release = release
        self.calls = 0

    def block(self):
        self.calls += 1
        self.started.set()
        self.release.wait(
            timeout=2.0
        )


class BlockingYahoo(
    BlockingProviderBase
):
    def get_quote(
        self,
        base_currency,
    ):
        self.block()

        return FxQuote(
            base_currency="USD",
            quote_currency="PLN",
            rate=4.0,
            provider=(
                "YAHOO_FINANCE_V8_CHART"
            ),
            provider_timestamp=(
                NOW
                - timedelta(
                    seconds=10
                )
            ),
            observed_at=NOW,
            source_quality=(
                FxSourceQuality.STALE_PRONE
            ),
        )


class ImmediateNbp:
    def __init__(self):
        self.calls = 0

    def get_reference(
        self,
        currency,
        *,
        effective_date=None,
    ):
        self.calls += 1

        return FxQuote(
            base_currency="USD",
            quote_currency="PLN",
            rate=3.9,
            provider="NBP_TABLE_A",
            provider_timestamp=None,
            observed_at=NOW,
            source_quality=(
                FxSourceQuality.DAILY_REFERENCE
            ),
            table="181/A/NBP/2026",
            effective_date=date(
                2026,
                9,
                17,
            ),
        )


class ImmediateCoinbase:
    def __init__(self):
        self.calls = 0

    def get_quote(self):
        self.calls += 1

        return FxQuote(
            base_currency="USDT",
            quote_currency="USD",
            rate=0.999,
            provider="COINBASE_EXCHANGE",
            provider_timestamp=(
                NOW
                - timedelta(
                    seconds=5
                )
            ),
            observed_at=NOW,
            source_quality=(
                FxSourceQuality.LIVE
            ),
            bid=0.9989,
            ask=0.9991,
        )


def test_timeout_is_fail_closed_and_does_not_wait_for_blocked_provider():
    started = threading.Event()
    release = threading.Event()

    yahoo = BlockingYahoo(
        started=started,
        release=release,
    )

    nbp = ImmediateNbp()
    coinbase = ImmediateCoinbase()

    resolver = (
        ParallelProductionFxResolver(
            prefetch_timeout_seconds=0.05,
            max_workers=3,
            clock=FixedClock(),
            yahoo_provider=yahoo,
            nbp_provider=nbp,
            coinbase_provider=coinbase,
        )
    )

    try:
        resolver.begin_cycle(
            [
                "BTCUSDT",
            ]
        )

        assert started.is_set()

        assert (
            resolver.last_prefetch_timed_out
            is True
        )

        assert (
            resolver.provider_errors[
                "MTM:USDPLN"
            ]
            == FX_PREFETCH_TIMEOUT
        )

        conversion = (
            resolver.conversion_for(
                "BTCUSDT"
            )
        )

        assert (
            conversion.converted_amount
            is None
        )

        assert (
            conversion.unavailable_reason
            == "MISSING_FX_LEG:USDPLN"
        )

    finally:
        release.set()


def test_next_prefetch_generation_is_blocked_while_prior_thread_is_alive():
    started = threading.Event()
    release = threading.Event()

    yahoo = BlockingYahoo(
        started=started,
        release=release,
    )

    nbp = ImmediateNbp()
    coinbase = ImmediateCoinbase()

    resolver = (
        ParallelProductionFxResolver(
            prefetch_timeout_seconds=0.05,
            max_workers=3,
            clock=FixedClock(),
            yahoo_provider=yahoo,
            nbp_provider=nbp,
            coinbase_provider=coinbase,
        )
    )

    try:
        resolver.begin_cycle(
            [
                "BTCUSDT",
            ]
        )

        first_counts = (
            yahoo.calls,
            nbp.calls,
            coinbase.calls,
        )

        assert (
            resolver.last_prefetch_timed_out
            is True
        )

        resolver.begin_cycle(
            [
                "BTCUSDT",
            ]
        )

        assert (
            resolver
            .last_prefetch_blocked_by_previous
            is True
        )

        assert (
            resolver.provider_errors[
                "PREFETCH"
            ]
            == PREVIOUS_FX_PREFETCH_STILL_RUNNING
        )

        assert (
            yahoo.calls,
            nbp.calls,
            coinbase.calls,
        ) == first_counts

    finally:
        release.set()


class ImmediateYahoo:
    def __init__(self):
        self.calls = []

    def get_quote(
        self,
        base_currency,
    ):
        base = str(
            base_currency
        ).upper()

        self.calls.append(
            base
        )

        return FxQuote(
            base_currency=base,
            quote_currency="PLN",
            rate=4.0,
            provider=(
                "YAHOO_FINANCE_V8_CHART"
            ),
            provider_timestamp=(
                NOW
                - timedelta(
                    seconds=10
                )
            ),
            observed_at=NOW,
            source_quality=(
                FxSourceQuality.STALE_PRONE
            ),
        )


def test_blocked_future_still_does_not_start_fx_tasks():
    yahoo = ImmediateYahoo()
    nbp = ImmediateNbp()
    coinbase = ImmediateCoinbase()

    resolver = (
        ParallelProductionFxResolver(
            prefetch_timeout_seconds=1.0,
            max_workers=3,
            clock=FixedClock(),
            yahoo_provider=yahoo,
            nbp_provider=nbp,
            coinbase_provider=coinbase,
        )
    )

    resolver.begin_cycle(
        [
            "GOLD_FUT_CONT",
        ]
    )

    assert yahoo.calls == []
    assert nbp.calls == 0
    assert coinbase.calls == 0

    assert (
        "GOLD_FUT_CONT"
        in resolver.contract_errors
    )

    assert (
        resolver.last_prefetch_duration_seconds
        == 0.0
    )


@pytest.mark.parametrize(
    "timeout,workers,match",
    [
        (
            0,
            1,
            "prefetch_timeout_seconds",
        ),
        (
            -1,
            1,
            "prefetch_timeout_seconds",
        ),
        (
            1,
            0,
            "max_workers",
        ),
        (
            1,
            -1,
            "max_workers",
        ),
        (
            1,
            1.5,
            "max_workers",
        ),
    ],
)
def test_scheduler_configuration_fails_closed(
    timeout,
    workers,
    match,
):
    with pytest.raises(
        ProductionFxSchedulerError,
        match=match,
    ):
        ParallelProductionFxResolver(
            prefetch_timeout_seconds=(
                timeout
            ),
            max_workers=workers,
            clock=FixedClock(),
            yahoo_provider=(
                ImmediateYahoo()
            ),
            nbp_provider=(
                ImmediateNbp()
            ),
            coinbase_provider=(
                ImmediateCoinbase()
            ),
        )
