from datetime import (
    date,
    datetime,
    timezone,
)
from decimal import Decimal
from types import SimpleNamespace

import pytest

from src.accounting.journal_entry_recovery import (
    JournalBackedPhase09AccountingRuntime,
    JournalEntryExecutionResolver,
    JournalEntryExecutionResolverError,
)
from src.accounting.runtime_bridge import (
    Phase09RuntimeAccountingBridge,
    RuntimeAccountingBridgeError,
)
from src.accounting.runtime_integration import (
    SnapshotCaptureDecisionProvider,
)
from src.execution.execution_journal import (
    RealisticExecutionJournal,
)
from src.execution.models import (
    BrokerResult,
    Execution,
    ExecutionProfile,
    Order,
    OrderIntent,
    OrderSide,
    OrderStatus,
    PaperMode,
)
from src.data.market_data import (
    ExecutionQuality,
)
from src.fx.models import (
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


def entry_execution(
    *,
    execution_id="entry-aapl",
    asset_id="AAPL",
    price=100.0,
    fee=0.2,
):
    return SimpleNamespace(
        execution_id=execution_id,
        asset_id=asset_id,
        side="BUY",
        quantity=2.0,
        execution_price=price,
        bid=99.9,
        ask=100.0,
        slippage=0.0,
        fee=fee,
    )


def exit_execution():
    return SimpleNamespace(
        execution_id="exit-aapl",
        asset_id="AAPL",
        side="SELL",
        quantity=2.0,
        execution_price=110.0,
        bid=110.0,
        ask=110.1,
        slippage=0.0,
        fee=0.22,
    )


def closed_position():
    return SimpleNamespace(
        position_id="pos-aapl",
        asset_id="AAPL",
        side="LONG",
        quantity=2.0,
        entry_execution_id="entry-aapl",
        entry_price=100.0,
        closed_at=NOW,
        exit_execution_id="exit-aapl",
    )


def committed_result(
    *,
    execution=None,
    intent="ENTRY",
    status="FILLED",
    asset_id="AAPL",
):
    if execution is None:
        execution = entry_execution(
            asset_id=asset_id
        )

    return SimpleNamespace(
        status=status,
        order=SimpleNamespace(
            intent=intent,
            asset_id=asset_id,
        ),
        execution=execution,
    )


class FakeJournal:
    def __init__(
        self,
        results,
    ):
        self.results = tuple(
            results
        )
        self.calls = 0

    def committed_results(self):
        self.calls += 1
        return self.results


def test_resolver_returns_exact_committed_entry_execution():
    execution = entry_execution()

    journal = FakeJournal(
        [
            committed_result(
                execution=execution
            ),
        ]
    )

    resolver = (
        JournalEntryExecutionResolver(
            journal
        )
    )

    result = resolver(
        asset_id="AAPL",
        position=closed_position(),
        entry_execution_id=(
            "entry-aapl"
        ),
    )

    assert result is execution
    assert journal.calls == 1


def test_resolver_returns_none_when_exact_execution_id_is_absent():
    journal = FakeJournal(
        [
            committed_result(
                execution=entry_execution(
                    execution_id="other"
                )
            ),
        ]
    )

    result = (
        JournalEntryExecutionResolver(
            journal
        )(
            asset_id="AAPL",
            position=closed_position(),
            entry_execution_id=(
                "entry-aapl"
            ),
        )
    )

    assert result is None


@pytest.mark.parametrize(
    "result,match",
    [
        (
            committed_result(
                intent="EXIT"
            ),
            "ENTRY_EXECUTION_JOURNAL_NOT_ENTRY",
        ),
        (
            committed_result(
                status="REJECTED"
            ),
            "ENTRY_EXECUTION_JOURNAL_NOT_FILLED",
        ),
        (
            committed_result(
                asset_id="BTCUSDT",
                execution=entry_execution(
                    asset_id="BTCUSDT"
                ),
            ),
            "ENTRY_EXECUTION_JOURNAL_ASSET_MISMATCH",
        ),
    ],
)
def test_resolver_rejects_matching_id_with_invalid_committed_evidence(
    result,
    match,
):
    resolver = (
        JournalEntryExecutionResolver(
            FakeJournal(
                [
                    result,
                ]
            )
        )
    )

    with pytest.raises(
        JournalEntryExecutionResolverError,
        match=match,
    ):
        resolver(
            asset_id="AAPL",
            position=closed_position(),
            entry_execution_id=(
                "entry-aapl"
            ),
        )


def test_resolver_rejects_duplicate_matching_execution_id():
    execution = entry_execution()

    resolver = (
        JournalEntryExecutionResolver(
            FakeJournal(
                [
                    committed_result(
                        execution=execution
                    ),
                    committed_result(
                        execution=execution
                    ),
                ]
            )
        )
    )

    with pytest.raises(
        JournalEntryExecutionResolverError,
        match="ENTRY_EXECUTION_JOURNAL_DUPLICATE",
    ):
        resolver(
            asset_id="AAPL",
            position=closed_position(),
            entry_execution_id=(
                "entry-aapl"
            ),
        )


def bridge():
    return (
        Phase09RuntimeAccountingBridge(
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
    )


def nbp_quote():
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


def accounting_runtime(
    *,
    entry_resolver,
):
    capture = (
        SnapshotCaptureDecisionProvider(
            lambda **kwargs: None
        )
    )

    runtime = SimpleNamespace(
        decision_provider=capture,
        positions={},
    )

    return (
        JournalBackedPhase09AccountingRuntime(
            runtime=runtime,
            accounting_bridge=bridge(),
            snapshot_capture=capture,
            fx_conversion_resolver=(
                lambda **kwargs: None
            ),
            estimated_exit_fee_resolver=(
                lambda **kwargs: 0
            ),
            realized_quotes_resolver=(
                lambda **kwargs: (
                    nbp_quote(),
                )
            ),
            entry_execution_resolver=(
                entry_resolver
            ),
        )
    )


def test_runtime_books_realized_from_journal_when_memory_cache_is_empty():
    recovered = entry_execution()

    runtime = accounting_runtime(
        entry_resolver=(
            lambda **kwargs: recovered
        )
    )

    assert runtime.entry_execution_ids == ()

    result = runtime._book_realized(
        asset_id="AAPL",
        position=closed_position(),
        exit_execution=(
            exit_execution()
        ),
    )

    assert (
        result.accounting_record
        .net_realized_pnl_native
        == Decimal("19.58")
    )

    assert (
        result.accounting_record
        .net_realized_pnl_pln
        == Decimal("78.320")
    )

    assert runtime.entry_execution_ids == ()


def test_runtime_keeps_fail_closed_when_journal_has_no_exact_entry():
    runtime = accounting_runtime(
        entry_resolver=(
            lambda **kwargs: None
        )
    )

    with pytest.raises(
        RuntimeAccountingBridgeError,
        match="ENTRY_EXECUTION_REQUIRED",
    ):
        runtime._book_realized(
            asset_id="AAPL",
            position=closed_position(),
            exit_execution=(
                exit_execution()
            ),
        )


def real_order():
    return Order(
        order_id="ord-entry-aapl",
        client_order_id="client-entry-aapl",
        asset_id="AAPL",
        side=OrderSide.BUY,
        quantity=2.0,
        intent=OrderIntent.ENTRY,
        created_at=NOW,
        execution_profile=(
            ExecutionProfile.REALISTIC_V2
        ),
        paper_mode=(
            PaperMode.REALISTIC_PAPER
        ),
    )


def real_execution():
    return Execution(
        execution_id="entry-aapl",
        order_id="ord-entry-aapl",
        asset_id="AAPL",
        side=OrderSide.BUY,
        quantity=2.0,
        reference_price=100.0,
        execution_price=100.0,
        bid=99.9,
        ask=100.0,
        spread=0.1,
        slippage=0.0,
        fee=0.2,
        provider_timestamp=NOW,
        execution_timestamp=NOW,
        data_quality="REALTIME",
        execution_quality=(
            ExecutionQuality.REAL_BOOK
        ),
        session_quality="EXCHANGE_CALENDAR",
        paper_mode=(
            PaperMode.REALISTIC_PAPER
        ),
        short_label=None,
        trigger_reason=None,
        pending_reason=None,
        execution_reason="FILLED",
        labels=(),
        config_hash="a" * 64,
    )


def test_real_execution_journal_recovers_full_entry_after_new_journal_instance(
    tmp_path,
):
    path = (
        tmp_path
        / "execution_journal.jsonl"
    )

    journal1 = (
        RealisticExecutionJournal(
            path,
            clock=FixedClock(),
        )
    )

    order = real_order()
    execution = real_execution()

    broker_result = BrokerResult(
        status=OrderStatus.FILLED,
        order=order,
        execution=execution,
        position=None,
    )

    journal1.prepare(
        order=order,
        order_fingerprint="fingerprint-entry",
    )

    journal1.commit(
        broker_result=broker_result,
        order_fingerprint="fingerprint-entry",
    )

    journal2 = (
        RealisticExecutionJournal(
            path,
            clock=FixedClock(),
        )
    )

    resolver = (
        JournalEntryExecutionResolver(
            journal2
        )
    )

    recovered = resolver(
        asset_id="AAPL",
        position=closed_position(),
        entry_execution_id=(
            "entry-aapl"
        ),
    )

    assert recovered == execution
    assert recovered.fee == 0.2
    assert recovered.bid == 99.9
    assert recovered.ask == 100.0
    assert recovered.slippage == 0.0
    assert recovered.config_hash == "a" * 64
