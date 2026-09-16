from datetime import datetime, timezone
from types import MappingProxyType, SimpleNamespace

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
)
from src.execution.paper_broker import PaperBroker
from src.execution.runtime import (
    RealisticPaperRuntime,
)
from src.execution.slippage import FixedBpsSlippage
from src.execution.state_store import (
    RealisticPaperStateStore,
)
from src.market.market_session import (
    MarketSessionSnapshot,
    SessionQuality,
    SessionState,
)


NOW = datetime(
    2026, 9, 16, 15, 0,
    tzinfo=timezone.utc,
)


class Asset:
    asset_id = "TEST"
    allow_long = True
    allow_short = False
    short_mechanism = "NONE"
    short_financing_model = None


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
        provider_status=ProviderStatus.CONNECTED,
        execution_quality=ExecutionQuality.REAL_BOOK,
    )


def session():
    return MarketSessionSnapshot(
        asset_id="TEST",
        session_id="TEST",
        state=SessionState.OPEN,
        session_quality=SessionQuality.EXCHANGE_CALENDAR,
        observed_at=NOW,
        timezone_name="UTC",
        local_time=NOW,
        reason="TEST",
        calendar_version="test-v1",
    )


def order():
    return Order(
        order_id="order-1",
        client_order_id="client-1",
        asset_id="TEST",
        side=OrderSide.BUY,
        quantity=1.0,
        intent=OrderIntent.ENTRY,
        created_at=NOW,
        execution_profile=ExecutionProfile.REALISTIC_V2,
        paper_mode=PaperMode.REALISTIC_PAPER,
        signal_reference="reconcile-test",
        stop_loss=95.0,
        take_profit=110.0,
    )


def broker(journal):
    return PaperBroker(
        clock=FixedClock(NOW),
        asset_resolver=lambda asset_id: Asset(),
        slippage_model=FixedBpsSlippage(0.0),
        trading_fee_rate=0.0,
        execution_journal=journal,
    )


class Market:
    def run_cycle(self, asset_ids):
        return SimpleNamespace(
            snapshots=MappingProxyType(
                {"TEST": snapshot()}
            ),
            errors=MappingProxyType({}),
            duration_seconds=0.1,
            timed_out=False,
        )


class Sessions:
    def get_session(self, asset_id, at):
        return session()


def no_decision(**kwargs):
    return None


def test_journal_reconstructs_expected_open_asset(
    tmp_path,
):
    journal = RealisticExecutionJournal(
        tmp_path / "journal.jsonl",
        clock=FixedClock(NOW),
    )

    b = broker(journal)

    result = b.submit_order(
        order(),
        market_snapshot=snapshot(),
        market_session=session(),
    )

    assert result.status is OrderStatus.FILLED

    b.commit_journal_result(result)

    assert (
        journal.expected_open_assets()
        == ("TEST",)
    )


def test_runtime_rejects_committed_entry_with_missing_state(
    tmp_path,
):
    journal_path = (
        tmp_path / "journal.jsonl"
    )

    journal1 = RealisticExecutionJournal(
        journal_path,
        clock=FixedClock(NOW),
    )

    b1 = broker(journal1)

    result = b1.submit_order(
        order(),
        market_snapshot=snapshot(),
        market_session=session(),
    )

    b1.commit_journal_result(result)

    journal2 = RealisticExecutionJournal(
        journal_path,
        clock=FixedClock(NOW),
    )

    with pytest.raises(
        RuntimeError,
        match="STATE_JOURNAL_MISMATCH",
    ):
        RealisticPaperRuntime(
            market_data_service=Market(),
            market_session_service=Sessions(),
            broker=broker(journal2),
            decision_provider=no_decision,
            clock=FixedClock(NOW),
            paper_mode=PaperMode.REALISTIC_PAPER,
            state_store=RealisticPaperStateStore(
                tmp_path / "missing-state.json",
                clock=FixedClock(NOW),
            ),
        )


def test_runtime_rejects_unresolved_wal_on_restart(
    tmp_path,
):
    journal_path = (
        tmp_path / "journal.jsonl"
    )

    journal1 = RealisticExecutionJournal(
        journal_path,
        clock=FixedClock(NOW),
    )

    b1 = broker(journal1)

    result = b1.submit_order(
        order(),
        market_snapshot=snapshot(),
        market_session=session(),
    )

    assert result.status is OrderStatus.FILLED

    # Intentionally no COMMIT.

    journal2 = RealisticExecutionJournal(
        journal_path,
        clock=FixedClock(NOW),
    )

    with pytest.raises(
        RuntimeError,
        match="RECOVERY_REQUIRED",
    ):
        RealisticPaperRuntime(
            market_data_service=Market(),
            market_session_service=Sessions(),
            broker=broker(journal2),
            decision_provider=no_decision,
            clock=FixedClock(NOW),
            paper_mode=PaperMode.REALISTIC_PAPER,
            state_store=RealisticPaperStateStore(
                tmp_path / "state.json",
                clock=FixedClock(NOW),
            ),
        )
