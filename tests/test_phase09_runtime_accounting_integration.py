from datetime import date, datetime, timezone
from decimal import Decimal
from types import MappingProxyType, SimpleNamespace

from src.accounting.runtime_bridge import (
    ACCOUNTING_PERSISTENCE_LIMITATION,
    Phase09RuntimeAccountingBridge,
)
from src.accounting.runtime_integration import (
    ACCOUNTING_FAIL_CLOSED,
    ENTRY_EXECUTION_CACHE_IN_MEMORY_ONLY,
    Phase09AccountingRuntime,
    SnapshotCaptureDecisionProvider,
)
from src.fx.models import (
    FxConversionResult,
    FxFreshness,
    FxPath,
    FxQuote,
    FxSourceQuality,
)
from src.fx.realized_booking import (
    RealizedFxBooker,
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

BOOKED_AT = datetime(
    2026,
    9,
    17,
    13,
    0,
    tzinfo=UTC,
)


class FixedClock:
    def now(self):
        return BOOKED_AT


def execution(
    *,
    execution_id,
    asset_id,
    side,
    price,
    fee,
):
    return SimpleNamespace(
        execution_id=execution_id,
        asset_id=asset_id,
        side=side,
        quantity=1.0,
        reference_price=price,
        execution_price=price,
        bid=price,
        ask=price + 0.1,
        spread=0.1,
        slippage=0.0,
        fee=fee,
    )


def position(
    *,
    asset_id,
    position_id,
    entry_execution_id,
    entry_price,
    closed_at=None,
    exit_execution_id=None,
):
    return SimpleNamespace(
        position_id=position_id,
        asset_id=asset_id,
        side="LONG",
        quantity=1.0,
        entry_execution_id=(
            entry_execution_id
        ),
        entry_price=entry_price,
        closed_at=closed_at,
        exit_execution_id=(
            exit_execution_id
        ),
    )


def snapshot(
    asset_id,
    *,
    bid,
    ask,
):
    return SimpleNamespace(
        asset_id=asset_id,
        bid=bid,
        ask=ask,
    )


def broker_result(
    *,
    execution_value=None,
    position_value=None,
):
    return SimpleNamespace(
        execution=execution_value,
        position=position_value,
    )


def asset_result(
    *,
    broker=None,
):
    return SimpleNamespace(
        broker_result=broker,
    )


def fx_conversion(
    source_currency,
    rate,
):
    if source_currency == "USDT":
        currencies = (
            "USDT",
            "USD",
            "PLN",
        )
    elif source_currency == "USD":
        currencies = (
            "USD",
            "PLN",
        )
    elif source_currency == "EUR":
        currencies = (
            "EUR",
            "PLN",
        )
    else:
        currencies = (
            source_currency,
            "PLN",
        )

    return FxConversionResult(
        source_amount=1.0,
        source_currency=(
            source_currency
        ),
        target_currency="PLN",
        converted_amount=rate,
        fx_path=FxPath(
            currencies
        ),
        freshness=FxFreshness.FX_FRESH,
        quote_age_seconds=10.0,
        legs=(),
        limitations=(),
        unavailable_reason=None,
    )


def nbp_usd_quote():
    return FxQuote(
        base_currency="USD",
        quote_currency="PLN",
        rate=4.0,
        provider="NBP_TABLE_A",
        provider_timestamp=None,
        observed_at=BOOKED_AT,
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


class NoDecision:
    def __call__(
        self,
        *,
        asset_id,
        snapshot,
        position,
    ):
        return None


class FakeRuntime:
    def __init__(
        self,
        *,
        decision_provider,
        steps,
    ):
        self.decision_provider = (
            decision_provider
        )
        self._steps = list(
            steps
        )
        self.positions = {}

    def run_cycle(
        self,
        asset_ids,
    ):
        step = self._steps.pop(0)

        for asset_id in asset_ids:
            market_snapshot = (
                step["snapshots"].get(
                    asset_id
                )
            )

            if market_snapshot is not None:
                self.decision_provider(
                    asset_id=asset_id,
                    snapshot=market_snapshot,
                    position=(
                        self.positions.get(
                            asset_id
                        )
                    ),
                )

        self.positions = dict(
            step["positions_after"]
        )

        return SimpleNamespace(
            results=MappingProxyType(
                dict(
                    step["results"]
                )
            ),
            market_data_errors=(
                MappingProxyType(
                    {}
                )
            ),
            duration_seconds=0.0,
            timed_out=False,
        )


def bridge():
    return Phase09RuntimeAccountingBridge(
        fx_enabled=True,
        pln_accounting_enabled=True,
        realized_fx_selection_policy=(
            RealizedFxSelectionPolicy(
                market_max_age_seconds=7200,
                daily_reference_max_age_days=7,
            )
        ),
        realized_fx_booker=(
            RealizedFxBooker(
                clock=FixedClock()
            )
        ),
    )


def integration(
    runtime,
    capture,
    *,
    include_realized=True,
):
    def fx_resolver(
        *,
        asset_id,
        position,
        market_snapshot,
    ):
        if asset_id.endswith(
            "USDT"
        ):
            return fx_conversion(
                "USDT",
                4.0,
            )

        return fx_conversion(
            "USD",
            4.0,
        )

    def exit_fee(
        *,
        asset_id,
        position,
        market_snapshot,
    ):
        return "0"

    def realized_quotes(
        *,
        asset_id,
        position,
        entry_execution,
        exit_execution,
    ):
        return (
            nbp_usd_quote(),
        )

    return Phase09AccountingRuntime(
        runtime=runtime,
        accounting_bridge=bridge(),
        snapshot_capture=capture,
        fx_conversion_resolver=(
            fx_resolver
        ),
        estimated_exit_fee_resolver=(
            exit_fee
        ),
        realized_quotes_resolver=(
            realized_quotes
            if include_realized
            else None
        ),
        cash_pln_resolver=(
            lambda: "1000"
        ),
    )


def test_snapshot_capture_is_transparent():
    calls = []

    class Delegate:
        def __call__(
            self,
            *,
            asset_id,
            snapshot,
            position,
        ):
            calls.append(
                (
                    asset_id,
                    snapshot,
                    position,
                )
            )
            return "DECISION"

    capture = (
        SnapshotCaptureDecisionProvider(
            Delegate()
        )
    )

    snap = snapshot(
        "AAPL",
        bid=100.0,
        ask=100.1,
    )

    result = capture(
        asset_id="AAPL",
        snapshot=snap,
        position=None,
    )

    assert result == "DECISION"
    assert (
        capture.snapshot_for(
            "AAPL"
        )
        is snap
    )
    assert calls == [
        (
            "AAPL",
            snap,
            None,
        )
    ]


def test_entry_cycle_caches_full_execution_and_marks_open_position():
    capture = (
        SnapshotCaptureDecisionProvider(
            NoDecision()
        )
    )

    entry_execution = execution(
        execution_id="entry-aapl",
        asset_id="AAPL",
        side="BUY",
        price=100.0,
        fee=0.2,
    )

    open_position = position(
        asset_id="AAPL",
        position_id="pos-aapl",
        entry_execution_id=(
            "entry-aapl"
        ),
        entry_price=100.0,
    )

    runtime = FakeRuntime(
        decision_provider=capture,
        steps=[
            {
                "snapshots": {
                    "AAPL": snapshot(
                        "AAPL",
                        bid=105.0,
                        ask=105.1,
                    ),
                },
                "positions_after": {
                    "AAPL": open_position,
                },
                "results": {
                    "AAPL": asset_result(
                        broker=broker_result(
                            execution_value=(
                                entry_execution
                            ),
                            position_value=(
                                open_position
                            ),
                        )
                    ),
                },
            },
        ],
    )

    wrapped = integration(
        runtime,
        capture,
    )

    result = wrapped.run_cycle(
        ["AAPL"]
    )

    item = result.accounting_results[
        "AAPL"
    ]

    assert item.error is None
    assert item.mtm_record is not None
    assert (
        item.mtm_record
        .unrealized_pnl_pln
        == 20
    )
    assert (
        "entry-aapl"
        in wrapped.entry_execution_ids
    )
    assert (
        ENTRY_EXECUTION_CACHE_IN_MEMORY_ONLY
        in item.limitations
    )
    assert (
        result.portfolio_snapshot
        .equity_pln
        == 1020
    )


def test_round_trip_uses_cached_full_entry_execution_for_realized_pln():
    capture = (
        SnapshotCaptureDecisionProvider(
            NoDecision()
        )
    )

    entry_execution = execution(
        execution_id="entry-aapl",
        asset_id="AAPL",
        side="BUY",
        price=100.0,
        fee=0.2,
    )

    exit_execution = execution(
        execution_id="exit-aapl",
        asset_id="AAPL",
        side="SELL",
        price=110.0,
        fee=0.22,
    )

    open_position = position(
        asset_id="AAPL",
        position_id="pos-aapl",
        entry_execution_id=(
            "entry-aapl"
        ),
        entry_price=100.0,
    )

    closed_position = position(
        asset_id="AAPL",
        position_id="pos-aapl",
        entry_execution_id=(
            "entry-aapl"
        ),
        entry_price=100.0,
        closed_at=NOW,
        exit_execution_id=(
            "exit-aapl"
        ),
    )

    runtime = FakeRuntime(
        decision_provider=capture,
        steps=[
            {
                "snapshots": {
                    "AAPL": snapshot(
                        "AAPL",
                        bid=100.0,
                        ask=100.1,
                    ),
                },
                "positions_after": {
                    "AAPL": open_position,
                },
                "results": {
                    "AAPL": asset_result(
                        broker=broker_result(
                            execution_value=(
                                entry_execution
                            ),
                            position_value=(
                                open_position
                            ),
                        )
                    ),
                },
            },
            {
                "snapshots": {
                    "AAPL": snapshot(
                        "AAPL",
                        bid=110.0,
                        ask=110.1,
                    ),
                },
                "positions_after": {},
                "results": {
                    "AAPL": asset_result(
                        broker=broker_result(
                            execution_value=(
                                exit_execution
                            ),
                            position_value=(
                                closed_position
                            ),
                        )
                    ),
                },
            },
        ],
    )

    wrapped = integration(
        runtime,
        capture,
    )

    wrapped.run_cycle(
        ["AAPL"]
    )

    result = wrapped.run_cycle(
        ["AAPL"]
    )

    item = result.accounting_results[
        "AAPL"
    ]

    assert item.error is None
    assert (
        item.realized_result
        .accounting_record
        .net_realized_pnl_native
        == Decimal("9.58")
    )
    assert (
        item.realized_result
        .accounting_record
        .net_realized_pnl_pln
        == Decimal("38.320")
    )
    assert (
        item.realized_result
        .fx_booking
        .fx_provider
        == "NBP_TABLE_A"
    )
    assert (
        ACCOUNTING_PERSISTENCE_LIMITATION
        in item.limitations
    )
    assert (
        "entry-aapl"
        not in wrapped.entry_execution_ids
    )


def test_restart_without_entry_execution_fails_closed_but_execution_cycle_survives():
    capture = (
        SnapshotCaptureDecisionProvider(
            NoDecision()
        )
    )

    exit_execution = execution(
        execution_id="exit-aapl",
        asset_id="AAPL",
        side="SELL",
        price=110.0,
        fee=0.22,
    )

    closed_position = position(
        asset_id="AAPL",
        position_id="pos-aapl",
        entry_execution_id=(
            "entry-aapl"
        ),
        entry_price=100.0,
        closed_at=NOW,
        exit_execution_id=(
            "exit-aapl"
        ),
    )

    runtime = FakeRuntime(
        decision_provider=capture,
        steps=[
            {
                "snapshots": {
                    "AAPL": snapshot(
                        "AAPL",
                        bid=110.0,
                        ask=110.1,
                    ),
                },
                "positions_after": {},
                "results": {
                    "AAPL": asset_result(
                        broker=broker_result(
                            execution_value=(
                                exit_execution
                            ),
                            position_value=(
                                closed_position
                            ),
                        )
                    ),
                },
            },
        ],
    )

    wrapped = integration(
        runtime,
        capture,
    )

    result = wrapped.run_cycle(
        ["AAPL"]
    )

    item = result.accounting_results[
        "AAPL"
    ]

    assert (
        "ENTRY_EXECUTION_REQUIRED"
        in item.error
    )
    assert (
        ACCOUNTING_FAIL_CLOSED
        in item.limitations
    )
    assert (
        result.execution_cycle
        is not None
    )


def test_missing_realized_quotes_resolver_fails_closed():
    capture = (
        SnapshotCaptureDecisionProvider(
            NoDecision()
        )
    )

    entry_execution = execution(
        execution_id="entry-aapl",
        asset_id="AAPL",
        side="BUY",
        price=100.0,
        fee=0.2,
    )

    exit_execution = execution(
        execution_id="exit-aapl",
        asset_id="AAPL",
        side="SELL",
        price=110.0,
        fee=0.22,
    )

    open_position = position(
        asset_id="AAPL",
        position_id="pos-aapl",
        entry_execution_id=(
            "entry-aapl"
        ),
        entry_price=100.0,
    )

    closed_position = position(
        asset_id="AAPL",
        position_id="pos-aapl",
        entry_execution_id=(
            "entry-aapl"
        ),
        entry_price=100.0,
        closed_at=NOW,
        exit_execution_id=(
            "exit-aapl"
        ),
    )

    runtime = FakeRuntime(
        decision_provider=capture,
        steps=[
            {
                "snapshots": {
                    "AAPL": snapshot(
                        "AAPL",
                        bid=100.0,
                        ask=100.1,
                    ),
                },
                "positions_after": {
                    "AAPL": open_position,
                },
                "results": {
                    "AAPL": asset_result(
                        broker=broker_result(
                            execution_value=(
                                entry_execution
                            ),
                            position_value=(
                                open_position
                            ),
                        )
                    ),
                },
            },
            {
                "snapshots": {
                    "AAPL": snapshot(
                        "AAPL",
                        bid=110.0,
                        ask=110.1,
                    ),
                },
                "positions_after": {},
                "results": {
                    "AAPL": asset_result(
                        broker=broker_result(
                            execution_value=(
                                exit_execution
                            ),
                            position_value=(
                                closed_position
                            ),
                        )
                    ),
                },
            },
        ],
    )

    wrapped = integration(
        runtime,
        capture,
        include_realized=False,
    )

    wrapped.run_cycle(
        ["AAPL"]
    )

    result = wrapped.run_cycle(
        ["AAPL"]
    )

    assert (
        "REALIZED_FX_QUOTES_RESOLVER_REQUIRED"
        in result
        .accounting_results[
            "AAPL"
        ]
        .error
    )


def test_multi_asset_accounting_failure_is_isolated_per_asset():
    capture = (
        SnapshotCaptureDecisionProvider(
            NoDecision()
        )
    )

    btc_entry = execution(
        execution_id="entry-btc",
        asset_id="BTCUSDT",
        side="BUY",
        price=100.0,
        fee=0.0,
    )

    btc_position = position(
        asset_id="BTCUSDT",
        position_id="pos-btc",
        entry_execution_id="entry-btc",
        entry_price=100.0,
    )

    future_position = position(
        asset_id="GOLD_FUT_CONT",
        position_id="pos-gold",
        entry_execution_id="entry-gold",
        entry_price=2000.0,
    )

    future_entry = execution(
        execution_id="entry-gold",
        asset_id="GOLD_FUT_CONT",
        side="BUY",
        price=2000.0,
        fee=0.0,
    )

    runtime = FakeRuntime(
        decision_provider=capture,
        steps=[
            {
                "snapshots": {
                    "BTCUSDT": snapshot(
                        "BTCUSDT",
                        bid=105.0,
                        ask=105.1,
                    ),
                    "GOLD_FUT_CONT": snapshot(
                        "GOLD_FUT_CONT",
                        bid=2010.0,
                        ask=2010.5,
                    ),
                },
                "positions_after": {
                    "BTCUSDT": btc_position,
                    "GOLD_FUT_CONT": (
                        future_position
                    ),
                },
                "results": {
                    "BTCUSDT": asset_result(
                        broker=broker_result(
                            execution_value=(
                                btc_entry
                            ),
                            position_value=(
                                btc_position
                            ),
                        )
                    ),
                    "GOLD_FUT_CONT": (
                        asset_result(
                            broker=broker_result(
                                execution_value=(
                                    future_entry
                                ),
                                position_value=(
                                    future_position
                                ),
                            )
                        )
                    ),
                },
            },
        ],
    )

    wrapped = integration(
        runtime,
        capture,
    )

    result = wrapped.run_cycle(
        [
            "BTCUSDT",
            "GOLD_FUT_CONT",
        ]
    )

    btc = result.accounting_results[
        "BTCUSDT"
    ]

    gold = result.accounting_results[
        "GOLD_FUT_CONT"
    ]

    assert btc.error is None
    assert btc.mtm_record is not None

    assert gold.error is not None
    assert (
        "ACCOUNTING_CONTRACT_BLOCKED"
        in gold.error
    )

    assert (
        ACCOUNTING_FAIL_CLOSED
        in result.limitations
    )

    assert result.portfolio_snapshot is None


def test_constructor_rejects_runtime_not_using_capture_wrapper():
    capture = (
        SnapshotCaptureDecisionProvider(
            NoDecision()
        )
    )

    runtime = SimpleNamespace(
        decision_provider=NoDecision(),
        positions={},
    )

    try:
        Phase09AccountingRuntime(
            runtime=runtime,
            accounting_bridge=bridge(),
            snapshot_capture=capture,
            fx_conversion_resolver=(
                lambda **kwargs: None
            ),
            estimated_exit_fee_resolver=(
                lambda **kwargs: 0
            ),
        )
    except ValueError as exc:
        assert (
            "RUNTIME_DECISION_PROVIDER_NOT_CAPTURE_WRAPPER"
            in str(exc)
        )
    else:
        raise AssertionError(
            "expected fail-closed constructor"
        )
