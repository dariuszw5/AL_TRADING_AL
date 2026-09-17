from datetime import (
    date,
    datetime,
    timedelta,
    timezone,
)
from decimal import Decimal
from types import SimpleNamespace

import pytest

from src.accounting.production_resolvers import (
    BrokerExitFeeEstimator,
    Phase10ProductionAccountingError,
    ProductionFxResolver,
    wire_phase10_production_accounting,
)
from src.fx.models import (
    FxFreshness,
    FxQuote,
    FxSourceQuality,
)
from src.fx.realized_selection import (
    RealizedFxSelectionPolicy,
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
    def __init__(
        self,
        value=NOW,
    ):
        self.value = value

    def now(self):
        return self.value


class FakeYahoo:
    def __init__(
        self,
        clock,
    ):
        self.clock = clock
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

        rates = {
            "USD": 4.0,
            "EUR": 4.5,
        }

        return FxQuote(
            base_currency=base,
            quote_currency="PLN",
            rate=rates[base],
            provider=(
                "YAHOO_FINANCE_V8_CHART"
            ),
            provider_timestamp=(
                self.clock.now()
                - timedelta(
                    seconds=30
                )
            ),
            observed_at=(
                self.clock.now()
            ),
            source_quality=(
                FxSourceQuality.STALE_PRONE
            ),
            labels=(
                "UNOFFICIAL",
                "DEGRADED_BY_DESIGN",
            ),
        )


class FakeNbp:
    def __init__(
        self,
        clock,
    ):
        self.clock = clock
        self.calls = []

    def get_reference(
        self,
        currency,
        *,
        effective_date=None,
    ):
        currency = str(
            currency
        ).upper()

        self.calls.append(
            (
                currency,
                effective_date,
            )
        )

        rates = {
            "USD": 3.9,
            "EUR": 4.4,
        }

        return FxQuote(
            base_currency=currency,
            quote_currency="PLN",
            rate=rates[currency],
            provider="NBP_TABLE_A",
            provider_timestamp=None,
            observed_at=(
                self.clock.now()
            ),
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


class FakeCoinbase:
    def __init__(
        self,
        clock,
        *,
        fail=False,
    ):
        self.clock = clock
        self.fail = fail
        self.calls = 0

    def get_quote(self):
        self.calls += 1

        if self.fail:
            raise RuntimeError(
                "coinbase unavailable"
            )

        return FxQuote(
            base_currency="USDT",
            quote_currency="USD",
            rate=0.999,
            provider="COINBASE_EXCHANGE",
            provider_timestamp=(
                self.clock.now()
                - timedelta(
                    seconds=5
                )
            ),
            observed_at=(
                self.clock.now()
            ),
            source_quality=(
                FxSourceQuality.LIVE
            ),
            bid=0.9989,
            ask=0.9991,
        )


def resolver(
    *,
    coinbase_fail=False,
):
    clock = FixedClock()

    yahoo = FakeYahoo(
        clock
    )

    nbp = FakeNbp(
        clock
    )

    coinbase = FakeCoinbase(
        clock,
        fail=coinbase_fail,
    )

    value = ProductionFxResolver(
        clock=clock,
        nbp_provider=nbp,
        yahoo_provider=yahoo,
        coinbase_provider=coinbase,
    )

    return (
        value,
        clock,
        yahoo,
        nbp,
        coinbase,
    )


def test_btc_prefetches_only_required_usdt_path_evidence():
    (
        value,
        clock,
        yahoo,
        nbp,
        coinbase,
    ) = resolver()

    value.begin_cycle(
        [
            "BTCUSDT",
        ]
    )

    assert yahoo.calls == [
        "USD",
    ]

    assert nbp.calls == [
        (
            "USD",
            None,
        )
    ]

    assert coinbase.calls == 1

    assert {
        quote.pair
        for quote in value.mtm_quotes
    } == {
        "USDPLN",
        "USDTUSD",
    }

    assert {
        quote.pair
        for quote in value.realized_quotes
    } == {
        "USDPLN",
        "USDTUSD",
    }


def test_usdt_mtm_uses_explicit_two_leg_conversion():
    (
        value,
        clock,
        yahoo,
        nbp,
        coinbase,
    ) = resolver()

    value.begin_cycle(
        [
            "BTCUSDT",
        ]
    )

    result = value.conversion_for(
        "BTCUSDT"
    )

    assert result.source_amount == 1.0
    assert result.source_currency == "USDT"
    assert result.target_currency == "PLN"
    assert result.fx_path.text == "USDT→USD→PLN"
    assert result.freshness is FxFreshness.FX_FRESH
    assert result.converted_amount == pytest.approx(
        3.996
    )


def test_missing_coinbase_leg_fails_closed_without_usdt_equals_usd():
    (
        value,
        clock,
        yahoo,
        nbp,
        coinbase,
    ) = resolver(
        coinbase_fail=True
    )

    value.begin_cycle(
        [
            "BTCUSDT",
        ]
    )

    result = value.conversion_for(
        "BTCUSDT"
    )

    assert (
        result.freshness
        is FxFreshness.FX_UNAVAILABLE
    )

    assert result.converted_amount is None

    assert (
        result.unavailable_reason
        == "MISSING_FX_LEG:USDTUSD"
    )

    assert (
        "MARKET:USDTUSD"
        in value.provider_errors
    )


def test_same_day_nbp_reference_is_prefetched_before_close():
    (
        value,
        clock,
        yahoo,
        nbp,
        coinbase,
    ) = resolver()

    value.begin_cycle(
        [
            "BTCUSDT",
        ]
    )

    close_time = (
        clock.now()
        + timedelta(
            minutes=1
        )
    )

    selected = (
        RealizedFxSelectionPolicy(
            market_max_age_seconds=7200,
            daily_reference_max_age_days=7,
        )
        .select(
            closed_at=close_time,
            native_currency="USDT",
            quotes=(
                value.realized_quotes_for(
                    "BTCUSDT"
                )
            ),
        )
    )

    assert [
        quote.pair
        for quote in selected
    ] == [
        "USDTUSD",
        "USDPLN",
    ]

    nbp_quote = selected[1]

    assert (
        nbp_quote.observed_at
        <= close_time
    )

    assert (
        nbp_quote.effective_date
        == close_time.date()
    )


@pytest.mark.parametrize(
    "asset_ids, expected_yahoo, expected_nbp, expected_coinbase",
    [
        (
            [
                "AAPL",
            ],
            [
                "USD",
            ],
            [
                (
                    "USD",
                    None,
                ),
            ],
            0,
        ),
        (
            [
                "EURUSD",
            ],
            [
                "USD",
            ],
            [
                (
                    "USD",
                    None,
                ),
            ],
            0,
        ),
        (
            [
                "AAPL",
                "BTCUSDT",
                "EURUSD",
            ],
            [
                "USD",
            ],
            [
                (
                    "USD",
                    None,
                ),
            ],
            1,
        ),
    ],
)
def test_prefetch_deduplicates_shared_currency_paths(
    asset_ids,
    expected_yahoo,
    expected_nbp,
    expected_coinbase,
):
    (
        value,
        clock,
        yahoo,
        nbp,
        coinbase,
    ) = resolver()

    value.begin_cycle(
        asset_ids
    )

    assert yahoo.calls == expected_yahoo
    assert nbp.calls == expected_nbp
    assert coinbase.calls == expected_coinbase


def test_blocked_future_does_not_trigger_fx_network_path():
    (
        value,
        clock,
        yahoo,
        nbp,
        coinbase,
    ) = resolver()

    value.begin_cycle(
        [
            "GOLD_FUT_CONT",
        ]
    )

    assert yahoo.calls == []
    assert nbp.calls == []
    assert coinbase.calls == 0

    assert (
        "GOLD_FUT_CONT"
        in value.contract_errors
    )


@pytest.mark.parametrize(
    "side,bid,ask,expected",
    [
        (
            "LONG",
            "110",
            "111",
            Decimal("0.0440"),
        ),
        (
            "SHORT",
            "110",
            "111",
            Decimal("0.0444"),
        ),
    ],
)
def test_exit_fee_estimator_uses_liquidation_side_mark(
    side,
    bid,
    ask,
    expected,
):
    broker = SimpleNamespace(
        trading_fee_rate=0.0004
    )

    estimator = (
        BrokerExitFeeEstimator(
            broker
        )
    )

    position = SimpleNamespace(
        asset_id="AAPL",
        side=side,
        quantity="1",
    )

    snapshot = SimpleNamespace(
        asset_id="AAPL",
        bid=bid,
        ask=ask,
    )

    assert estimator(
        asset_id="AAPL",
        position=position,
        market_snapshot=snapshot,
    ) == expected


def test_exit_fee_estimator_rejects_asset_mismatch():
    estimator = (
        BrokerExitFeeEstimator(
            SimpleNamespace(
                trading_fee_rate=0.0004
            )
        )
    )

    with pytest.raises(
        Phase10ProductionAccountingError,
        match="EXIT_FEE_ASSET_MISMATCH",
    ):
        estimator(
            asset_id="AAPL",
            position=SimpleNamespace(
                asset_id="AAPL",
                side="LONG",
                quantity="1",
            ),
            market_snapshot=SimpleNamespace(
                asset_id="BTCUSDT",
                bid="100",
                ask="101",
            ),
        )


class Delegate:
    def __init__(self):
        self.calls = []

    def __call__(
        self,
        *,
        asset_id,
        snapshot,
        position,
    ):
        self.calls.append(
            (
                asset_id,
                snapshot,
                position,
            )
        )
        return "UNCHANGED_DECISION"


class FakeRuntime:
    def __init__(
        self,
        *,
        broker,
        clock,
    ):
        self.broker = broker
        self.clock = clock
        self.decision_provider = (
            Delegate()
        )
        self.positions = {}

    def run_cycle(
        self,
        asset_ids,
    ):
        return SimpleNamespace(
            results={},
        )


def test_wiring_wraps_decision_provider_without_changing_delegate_result():
    (
        fx_resolver,
        clock,
        yahoo,
        nbp,
        coinbase,
    ) = resolver()

    broker = SimpleNamespace(
        trading_fee_rate=0.0004
    )

    runtime = FakeRuntime(
        broker=broker,
        clock=clock,
    )

    original = (
        runtime.decision_provider
    )

    wiring = (
        wire_phase10_production_accounting(
            runtime=runtime,
            broker=broker,
            realized_market_max_age_seconds=7200,
            realized_daily_reference_max_age_days=7,
            clock=clock,
            nbp_provider=nbp,
            yahoo_provider=yahoo,
            coinbase_provider=coinbase,
        )
    )

    snap = SimpleNamespace(
        asset_id="AAPL",
    )

    result = (
        runtime.decision_provider(
            asset_id="AAPL",
            snapshot=snap,
            position=None,
        )
    )

    assert result == "UNCHANGED_DECISION"
    assert original.calls == [
        (
            "AAPL",
            snap,
            None,
        )
    ]

    assert (
        wiring.accounting_runtime
        .cash_pln_resolver
        is None
    )


def test_wiring_rejects_broker_mismatch():
    clock = FixedClock()

    runtime = FakeRuntime(
        broker=SimpleNamespace(
            trading_fee_rate=0.0004
        ),
        clock=clock,
    )

    with pytest.raises(
        Phase10ProductionAccountingError,
        match="RUNTIME_BROKER_MISMATCH",
    ):
        wire_phase10_production_accounting(
            runtime=runtime,
            broker=SimpleNamespace(
                trading_fee_rate=0.0004
            ),
            realized_market_max_age_seconds=7200,
            realized_daily_reference_max_age_days=7,
            clock=clock,
        )


def test_realized_policy_thresholds_are_caller_supplied_not_silently_frozen():
    (
        value,
        clock,
        yahoo,
        nbp,
        coinbase,
    ) = resolver()

    broker = SimpleNamespace(
        trading_fee_rate=0.0004
    )

    runtime = FakeRuntime(
        broker=broker,
        clock=clock,
    )

    wiring = (
        wire_phase10_production_accounting(
            runtime=runtime,
            broker=broker,
            realized_market_max_age_seconds=1234,
            realized_daily_reference_max_age_days=5,
            clock=clock,
            nbp_provider=nbp,
            yahoo_provider=yahoo,
            coinbase_provider=coinbase,
        )
    )

    policy = (
        wiring.accounting_bridge
        .realized_fx_selection_policy
    )

    assert (
        policy.market_max_age_seconds
        == 1234.0
    )

    assert (
        policy.daily_reference_max_age_days
        == 5
    )


def test_prefetch_failure_state_is_fail_closed():
    (
        value,
        clock,
        yahoo,
        nbp,
        coinbase,
    ) = resolver()

    value.force_cycle_error(
        RuntimeError(
            "unexpected prefetch failure"
        )
    )

    with pytest.raises(
        Phase10ProductionAccountingError,
        match="PRODUCTION_FX_PREFETCH_FAILED",
    ):
        value.conversion_for(
            "BTCUSDT"
        )
