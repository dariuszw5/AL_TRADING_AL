from datetime import (
    datetime,
    timedelta,
    timezone,
)

import pytest

from src.core.clock import FixedClock
from src.data.market_data import (
    DataQuality,
    ExecutionQuality,
    MarketSnapshot,
    ProviderStatus,
)
from src.execution.execution_journal import (
    RealisticExecutionJournal,
)
from src.execution.models import (
    ExecutionProfile,
    Order,
    OrderIntent,
    OrderSide,
    OrderStatus,
    PaperMode,
    RejectionReason,
)
from src.execution.paper_broker import (
    PaperBroker,
)
from src.execution.runtime import (
    ExecutionDecision,
    RealisticPaperRuntime,
    RuntimeAssetStatus,
)
from src.execution.slippage import (
    FixedBpsSlippage,
)
from src.execution.state_store import (
    RealisticPaperStateStore,
)
from src.market.market_session import (
    MarketSessionSnapshot,
    SessionQuality,
    SessionState,
)


NOW = datetime(
    2026,
    9,
    16,
    15,
    0,
    tzinfo=timezone.utc,
)


class FakeAsset:
    asset_id = "TEST"
    allow_long = True
    allow_short = False
    short_mechanism = "NONE"
    short_financing_model = None


def resolver(asset_id):
    return FakeAsset()


def snapshot():
    return MarketSnapshot(
        asset_id="TEST",
        bid=100.0,
        ask=101.0,
        last=100.5,
        provider_timestamp=NOW,
        received_at=NOW,
        data_quality=DataQuality.REALTIME,
        delayed=False,
        quote_age_seconds=0.0,
        provider_status=(
            ProviderStatus.CONNECTED
        ),
        execution_quality=(
            ExecutionQuality.REAL_BOOK
        ),
    )


def session():
    return MarketSessionSnapshot(
        asset_id="TEST",
        session_id="TEST",
        state=SessionState.OPEN,
        session_quality=(
            SessionQuality.EXCHANGE_CALENDAR
        ),
        observed_at=NOW,
        timezone_name="UTC",
        local_time=NOW,
        reason="TEST",
        calendar_version="test-v1",
    )


def order(
    *,
    client_id="client-1",
    quantity=2.0,
    created_at=NOW,
):
    return Order(
        order_id=(
            f"order-{client_id}-"
            f"{created_at.timestamp()}"
        ),
        client_order_id=client_id,
        asset_id="TEST",
        side=OrderSide.BUY,
        quantity=quantity,
        intent=OrderIntent.ENTRY,
        created_at=created_at,
        execution_profile=(
            ExecutionProfile.REALISTIC_V2
        ),
        paper_mode=(
            PaperMode.REALISTIC_PAPER
        ),
        signal_reference="signal-1",
        stop_loss=95.0,
        take_profit=110.0,
    )


def broker(
    *,
    journal=None,
):
    return PaperBroker(
        clock=FixedClock(NOW),
        asset_resolver=resolver,
        slippage_model=(
            FixedBpsSlippage(0.0)
        ),
        trading_fee_rate=0.0,
        execution_journal=journal,
    )


def test_order_fingerprint_ignores_created_at_and_order_id():
    b = broker()

    first = order(
        created_at=NOW
    )

    second = order(
        created_at=(
            NOW
            + timedelta(
                seconds=10
            )
        )
    )

    assert (
        b.order_fingerprint(first)
        == b.order_fingerprint(second)
    )


def test_order_fingerprint_changes_with_quantity():
    b = broker()

    assert (
        b.order_fingerprint(
            order(quantity=2.0)
        )
        != b.order_fingerprint(
            order(quantity=3.0)
        )
    )


def test_committed_result_is_idempotent_after_restart(
    tmp_path,
):
    path = (
        tmp_path
        / "journal.jsonl"
    )

    journal1 = (
        RealisticExecutionJournal(
            path,
            clock=FixedClock(NOW),
        )
    )

    broker1 = broker(
        journal=journal1
    )

    first = broker1.submit_order(
        order(),
        market_snapshot=snapshot(),
        market_session=session(),
    )

    assert (
        first.status
        is OrderStatus.FILLED
    )

    broker1.commit_journal_result(
        first
    )

    assert (
        journal1
        .unresolved_client_order_ids()
        == ()
    )

    journal2 = (
        RealisticExecutionJournal(
            path,
            clock=FixedClock(
                NOW
                + timedelta(
                    minutes=1
                )
            ),
        )
    )

    broker2 = broker(
        journal=journal2
    )

    second = broker2.submit_order(
        order(
            created_at=(
                NOW
                + timedelta(
                    seconds=30
                )
            )
        ),
        market_snapshot=snapshot(),
        market_session=session(),
    )

    assert (
        second.status
        is OrderStatus.FILLED
    )

    assert (
        second.execution.execution_id
        == first.execution.execution_id
    )


def test_conflicting_payload_after_restart_is_rejected(
    tmp_path,
):
    path = (
        tmp_path
        / "journal.jsonl"
    )

    journal1 = (
        RealisticExecutionJournal(
            path,
            clock=FixedClock(NOW),
        )
    )

    broker1 = broker(
        journal=journal1
    )

    first = broker1.submit_order(
        order(quantity=2.0),
        market_snapshot=snapshot(),
        market_session=session(),
    )

    broker1.commit_journal_result(
        first
    )

    broker2 = broker(
        journal=(
            RealisticExecutionJournal(
                path,
                clock=FixedClock(NOW),
            )
        )
    )

    conflict = broker2.submit_order(
        order(
            quantity=3.0
        ),
        market_snapshot=snapshot(),
        market_session=session(),
    )

    assert (
        conflict.status
        is OrderStatus.REJECTED
    )

    assert (
        conflict.rejection_reason
        is RejectionReason.IDEMPOTENCY_CONFLICT
    )


def test_unresolved_prepare_blocks_asset_after_restart(
    tmp_path,
):
    path = (
        tmp_path
        / "journal.jsonl"
    )

    journal1 = (
        RealisticExecutionJournal(
            path,
            clock=FixedClock(NOW),
        )
    )

    broker1 = broker(
        journal=journal1
    )

    first = broker1.submit_order(
        order(),
        market_snapshot=snapshot(),
        market_session=session(),
    )

    assert (
        first.status
        is OrderStatus.FILLED
    )

    assert (
        journal1
        .unresolved_client_order_ids()
        == ("client-1",)
    )

    broker2 = broker(
        journal=(
            RealisticExecutionJournal(
                path,
                clock=FixedClock(NOW),
            )
        )
    )

    blocked = broker2.submit_order(
        order(
            client_id="client-2"
        ),
        market_snapshot=snapshot(),
        market_session=session(),
    )

    assert (
        blocked.status
        is OrderStatus.REJECTED
    )

    assert (
        blocked.rejection_reason
        is RejectionReason.RECOVERY_REQUIRED
    )


class FakeMarketDataService:

    def run_cycle(
        self,
        asset_ids,
    ):
        from types import (
            MappingProxyType,
            SimpleNamespace,
        )

        return SimpleNamespace(
            snapshots=(
                MappingProxyType(
                    {
                        "TEST": snapshot(),
                    }
                )
            ),
            errors=(
                MappingProxyType(
                    {}
                )
            ),
            duration_seconds=0.1,
            timed_out=False,
        )


class FakeSessionService:

    def get_session(
        self,
        asset_id,
        at,
    ):
        return session()


class OneDecision:

    def __call__(
        self,
        *,
        asset_id,
        snapshot,
        position,
    ):
        return ExecutionDecision(
            side=OrderSide.BUY,
            intent=OrderIntent.ENTRY,
            quantity=2.0,
            stop_loss=95.0,
            take_profit=110.0,
            signal_reference="runtime-test",
        )


def test_runtime_commits_journal_after_state_save(
    tmp_path,
):
    journal = (
        RealisticExecutionJournal(
            tmp_path
            / "journal.jsonl",
            clock=FixedClock(NOW),
        )
    )

    store = (
        RealisticPaperStateStore(
            tmp_path
            / "state.json",
            clock=FixedClock(NOW),
        )
    )

    runtime = (
        RealisticPaperRuntime(
            market_data_service=(
                FakeMarketDataService()
            ),
            market_session_service=(
                FakeSessionService()
            ),
            broker=broker(
                journal=journal
            ),
            decision_provider=(
                OneDecision()
            ),
            clock=FixedClock(NOW),
            paper_mode=(
                PaperMode.REALISTIC_PAPER
            ),
            state_store=store,
        )
    )

    result = runtime.run_cycle(
        ["TEST"]
    )

    assert (
        result.results["TEST"].status
        is RuntimeAssetStatus.FILLED
    )

    assert (
        journal
        .unresolved_client_order_ids()
        == ()
    )

    restored = (
        store.load_positions()
    )

    assert "TEST" in restored


class FailingStateStore:

    def load_positions(self):
        return {}

    def save_positions(
        self,
        positions,
    ):
        raise OSError(
            "simulated state write failure"
        )


def test_state_write_failure_leaves_unresolved_wal(
    tmp_path,
):
    path = (
        tmp_path
        / "journal.jsonl"
    )

    journal1 = (
        RealisticExecutionJournal(
            path,
            clock=FixedClock(NOW),
        )
    )

    runtime = (
        RealisticPaperRuntime(
            market_data_service=(
                FakeMarketDataService()
            ),
            market_session_service=(
                FakeSessionService()
            ),
            broker=broker(
                journal=journal1
            ),
            decision_provider=(
                OneDecision()
            ),
            clock=FixedClock(NOW),
            paper_mode=(
                PaperMode.REALISTIC_PAPER
            ),
            state_store=(
                FailingStateStore()
            ),
        )
    )

    with pytest.raises(
        OSError,
        match="simulated state write failure",
    ):
        runtime.run_cycle(
            ["TEST"]
        )

    assert (
        len(
            journal1
            .unresolved_client_order_ids()
        )
        == 1
    )

    broker2 = broker(
        journal=(
            RealisticExecutionJournal(
                path,
                clock=FixedClock(NOW),
            )
        )
    )

    blocked = broker2.submit_order(
        order(
            client_id="new-client"
        ),
        market_snapshot=snapshot(),
        market_session=session(),
    )

    assert (
        blocked.status
        is OrderStatus.REJECTED
    )

    assert (
        blocked.rejection_reason
        is RejectionReason.RECOVERY_REQUIRED
    )
